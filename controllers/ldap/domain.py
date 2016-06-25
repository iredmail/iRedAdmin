# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings
from libs import iredutils, form_utils
from libs.ldaplib import decorators, domain as domainlib, connUtils, ldaputils

session = web.config.get('_session')


#
# Domain related.
#


class List:
    '''List all virtual mail domains.'''
    @decorators.require_login
    def GET(self, cur_page=1):
        i = web.input()
        cur_page = int(cur_page)

        if cur_page == 0:
            cur_page == 1

        domainLib = domainlib.Domain()
        result = domainLib.listAccounts()
        if result[0] is True:
            allDomains = result[1]

            # Get value of accountSetting.
            allAccountSettings = ldaputils.getAccountSettingFromLdapQueryResult(allDomains, key='domainName',)
        else:
            return result

        connutils = connUtils.Utils()
        sl = connutils.getSizelimitFromAccountLists(allDomains, curPage=cur_page, sizelimit=settings.PAGE_SIZE_LIMIT,)

        if cur_page > sl.get('totalPages'):
            cur_page = sl.get('totalPages')

        return web.render(
            'ldap/domain/list.html',
            cur_page=cur_page,
            total=sl.get('totalAccounts'),
            allDomains=sl.get('accountList'),
            allAccountSettings=allAccountSettings,
            msg=i.get('msg', None),
        )

    @decorators.require_global_admin
    @decorators.csrf_protected
    @decorators.require_login
    def POST(self):
        i = web.input(domainName=[], _unicode=False,)

        self.domainName = i.get('domainName', [])
        action = i.get('action', None)

        domainLib = domainlib.Domain()

        if action == 'delete':
            keep_mailbox_days = form_utils.get_single_value(form=i,
                                                            input_name='keep_mailbox_days',
                                                            default_value=0,
                                                            is_integer=True)

            result = domainLib.delete(domains=self.domainName,
                                      keep_mailbox_days=keep_mailbox_days)
            msg = 'DELETED'
        elif action == 'disable':
            result = domainLib.enableOrDisableAccount(domains=self.domainName, action='disable',)
            msg = 'DISABLED'
        elif action == 'enable':
            result = domainLib.enableOrDisableAccount(domains=self.domainName, action='enable',)
            msg = 'ENABLED'
        else:
            result = (False, 'INVALID_ACTION')
            msg = i.get('msg', None)

        if result[0] is True:
            raise web.seeother('/domains?msg=%s' % msg)
        else:
            raise web.seeother('/domains?msg=' + web.urlquote(result[1]))


class Profile:
    @decorators.require_login
    def GET(self, profile_type, domain):
        i = web.input()
        self.domain = web.safestr(domain.split('/', 1)[0])
        self.profile_type = web.safestr(profile_type)

        if not iredutils.is_domain(self.domain):
            raise web.seeother('/domains?msg=EMPTY_DOMAIN')

        domainLib = domainlib.Domain()
        result = domainLib.profile(domain=self.domain)

        if result[0] is False:
            raise web.seeother('/domains?msg=' + web.urlquote(result[1]))

        r = domainLib.listAccounts(attrs=['domainName'])
        if r[0] is True:
            allDomains = r[1]
        else:
            return r

        allAccountSettings = ldaputils.getAccountSettingFromLdapQueryResult(result[1], key='domainName',)

        return web.render(
            'ldap/domain/profile.html',
            cur_domain=self.domain,
            allDomains=allDomains,
            allAccountSettings=allAccountSettings,
            profile=result[1],
            profile_type=self.profile_type,
            msg=i.get('msg', None),
        )

    @decorators.csrf_protected
    @decorators.require_login
    def POST(self, profile_type, domain):
        self.profile_type = web.safestr(profile_type)
        self.domain = web.safestr(domain)

        i = web.input(domainAliasName=[], enabledService=[], domainAdmin=[], defaultList=[],)

        if self.domain != web.safestr(i.get('domainName', None)).lower():
            raise web.seeother('/profile/domain/%s/%s?msg=DOMAIN_NAME_MISMATCH' % (self.profile_type, self.domain))

        domainLib = domainlib.Domain()
        result = domainLib.update(profile_type=self.profile_type,
                                  domain=self.domain,
                                  data=i)
        if result[0] is True:
            raise web.seeother('/profile/domain/%s/%s?msg=UPDATED' % (self.profile_type, self.domain))
        elif result[0] is False:
            raise web.seeother('/profile/domain/%s/%s?msg=%s' % (self.profile_type, self.domain, web.urlquote(result[1])))


class Create:
    @decorators.require_global_admin
    @decorators.require_login
    def GET(self):
        i = web.input()
        self.domain = web.safestr(i.get('domain', ''))
        return web.render('ldap/domain/create.html', msg=i.get('msg'), domainName=self.domain)

    @decorators.require_global_admin
    @decorators.csrf_protected
    @decorators.require_login
    def POST(self):
        i = web.input()
        self.domain = web.safestr(i.get('domainName')).strip().lower()
        domainLib = domainlib.Domain()
        result = domainLib.add(data=i)
        if result[0] is True:
            raise web.seeother('/profile/domain/general/%s?msg=CREATED' % self.domain)
        else:
            raise web.seeother('/create/domain?msg=%s' % web.urlquote(result[1]))
