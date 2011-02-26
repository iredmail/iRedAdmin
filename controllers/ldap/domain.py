# Author: Zhang Huangbin <zhb@iredmail.org>

import sys
import web
from controllers import base
from libs import iredutils
from libs.ldaplib import admin, domain as domainlib, user, connUtils, ldaputils

cfg = web.iredconfig
session = web.config.get('_session')


#
# Domain related.
#


class List:
    '''List all virtual mail domains.'''
    @base.require_login
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
        sl = connutils.getSizelimitFromAccountLists(allDomains, curPage=cur_page, sizelimit=session.get('pageSizeLimit', 50),)

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

    @base.require_global_admin
    @base.require_login
    def POST(self):
        i = web.input(domainName=[], _unicode=False,)

        self.domainName = i.get('domainName', [])
        self.action = i.get('action', None)

        domainLib = domainlib.Domain()

        if self.action == 'delete':
            result = domainLib.delete(domains=self.domainName)
            msg = 'DELETED_SUCCESS'
        elif self.action == 'disable':
            result = domainLib.enableOrDisableAccount(domains=self.domainName, action='disable',)
            msg = 'DISABLED_SUCCESS'
        elif self.action == 'enable':
            result = domainLib.enableOrDisableAccount(domains=self.domainName, action='enable',)
            msg = 'ENABLED_SUCCESS'
        else:
            result = (False, 'INVALID_ACTION')
            msg = i.get('msg', None)

        if result[0] is True:
            return web.seeother('/domains?msg=%s' % msg)
        else:
            return web.seeother('/domains?msg=' + result[1])


class Profile:
    @base.require_login
    def GET(self, profile_type, domain):
        i = web.input()
        self.domain = web.safestr(domain.split('/', 1)[0])
        self.profile_type = web.safestr(profile_type)

        if not iredutils.isDomain(self.domain):
            return web.seeother('/domains?msg=EMPTY_DOMAIN')

        domainLib = domainlib.Domain()
        result = domainLib.profile(domain=self.domain)

        if result[0] is True:
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
        else:
            return web.seeother('/domains?msg=' + result[1])

    @base.require_login
    def POST(self, profile_type, domain):
        self.profile_type = web.safestr(profile_type)
        self.domain = web.safestr(domain)

        i = web.input()

        if self.domain != web.safestr(i.get('domainName', None)):
            return web.seeother('/profile/domain/%s/%s?msg=DOMAIN_NAME_MISMATCH' % (self.profile_type, self.domain))

        domainLib = domainlib.Domain()
        result = domainLib.update(
                profile_type=self.profile_type,
                domain=self.domain,
                data=i,
                )
        if result[0] is True:
            return web.seeother('/profile/domain/%s/%s?msg=PROFILE_UPDATED_SUCCESS' % (self.profile_type, self.domain))
        elif result[0] is False:
            return web.seeother('/profile/domain/%s/%s?msg=%s' % (self.profile_type, self.domain, result[1]))


class Create:
    @base.require_global_admin
    @base.require_login
    def GET(self):
        i = web.input()
        self.domain = web.safestr(i.get('domain', ''))
        return web.render('ldap/domain/create.html', msg=i.get('msg'), domainName=self.domain)

    @base.require_global_admin
    @base.require_login
    def POST(self):
        i = web.input()
        self.domain = web.safestr(i.get('domainName')).strip().lower()
        domainLib = domainlib.Domain()
        result = domainLib.add(data=i)
        if result[0] is True:
            return web.seeother('/profile/domain/general/%s?msg=CREATED_SUCCESS' % self.domain)
        else:
            return web.seeother('/create/domain?msg=%s' % result[1])
