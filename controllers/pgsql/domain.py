# Author: Zhang Huangbin <zhb@iredmail.org>

import web
from libs import iredutils, form_utils
from libs.pgsql import decorators, domain as domainlib

session = web.config.get('_session')


#
# Domain related.
#


class List:
    '''List all virtual mail domains.'''
    @decorators.require_login
    def GET(self, cur_page=1,):
        i = web.input()

        try:
            cur_page = int(cur_page) or 1
        except:
            cur_page = 1

        domainLib = domainlib.Domain()
        result = domainLib.listAccounts(cur_page=cur_page)

        if result[0] is True:
            allDomains = result[2]

            return web.render(
                'pgsql/domain/list.html',
                cur_page=cur_page,
                total=result[1],
                allDomains=allDomains,
                msg=i.get('msg', None),
            )
        else:
            return web.render(
                'pgsql/domain/list.html',
                cur_page=cur_page,
                total=0,
                allDomains=[],
                msg=result[1],
            )

    @decorators.require_global_admin
    @decorators.csrf_protected
    @decorators.require_login
    def POST(self):
        i = web.input(domainName=[], _unicode=False,)
        domainName = i.get('domainName', None)
        action = i.get('action')

        domainLib = domainlib.Domain()
        if action == 'delete':
            keep_mailbox_days = form_utils.get_single_value(form=i,
                                                            input_name='keep_mailbox_days',
                                                            default_value=0,
                                                            is_integer=True)

            result = domainLib.delete(domains=domainName, keep_mailbox_days=keep_mailbox_days)
            msg = 'DELETED'
        elif action == 'disable':
            result = domainLib.enableOrDisableAccount(accounts=domainName, active=False,)
            msg = 'DISABLED'
        elif action == 'enable':
            result = domainLib.enableOrDisableAccount(accounts=domainName, active=True,)
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

        if result[0] is not True:
            raise web.seeother('/domains?msg=' + web.urlquote(result[1]))
        else:
            self.profile = result[1]

        return web.render(
            'pgsql/domain/profile.html',
            cur_domain=self.domain,
            profile_type=self.profile_type,
            profile=self.profile,
            msg=i.get('msg'),
        )

    @decorators.csrf_protected
    @decorators.require_login
    def POST(self, profile_type, domain):
        self.profile_type = str(profile_type)
        self.domain = str(domain)

        i = web.input(domainAliasName=[], domainAdmin=[], defaultList=[],)

        domainLib = domainlib.Domain()
        result = domainLib.update(
            profile_type=self.profile_type,
            domain=self.domain,
            data=i,
        )

        if result[0] is True:
            raise web.seeother('/profile/domain/%s/%s?msg=UPDATED' % (self.profile_type, self.domain))
        else:
            raise web.seeother('/profile/domain/%s/%s?msg=%s' % (self.profile_type, self.domain, web.urlquote(result[1]),))


class Create:
    @decorators.require_global_admin
    @decorators.require_login
    def GET(self):
        i = web.input()
        return web.render(
            'pgsql/domain/create.html',
            msg=i.get('msg'),
        )

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
