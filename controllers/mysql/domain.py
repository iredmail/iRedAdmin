# Author: Zhang Huangbin <zhb@iredmail.org>

import web
from controllers import base
from libs import iredutils
from libs.mysql import domain as domainlib

cfg = web.iredconfig
session = web.config.get('_session')

#
# Domain related.
#


class List:
    '''List all virtual mail domains.'''
    @base.require_login
    def GET(self, cur_page=1,):
        i = web.input()

        try:
            cur_page = int(cur_page)
            if cur_page == 0:
                cur_page == 1
        except:
            cur_page = 1

        domainLib = domainlib.Domain()
        result = domainLib.listAccounts(cur_page=cur_page)

        if result[0] is True:
            return web.render(
                'mysql/domain/list.html',
                cur_page=cur_page,
                total=result[1],
                allDomains=result[2],
                msg=i.get('msg', None),
            )
        else:
            return web.render(
                'mysql/domain/list.html',
                cur_page=cur_page,
                total=0,
                allDomains=[],
                msg=result[1],
            )

    @base.require_global_admin
    @base.require_login
    def POST(self):
        i = web.input(domainName=[], _unicode=False,)
        domainName = i.get('domainName', None)
        self.action = i.get('action')

        domainLib = domainlib.Domain()
        if self.action == 'delete':
            result = domainLib.delete(domains=domainName)
            msg = 'DELETED_SUCCESS'
        elif self.action == 'disable':
            result = domainLib.enableOrDisableAccount(accounts=domainName, active=False,)
            msg = 'DISABLED_SUCCESS'
        elif self.action == 'enable':
            result = domainLib.enableOrDisableAccount(accounts=domainName, active=True,)
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

        if result[0] is not True:
            return web.seeother('/domains?msg=' + result[1])
        else:
            self.profile = result[1]

        return web.render(
            'mysql/domain/profile.html',
            cur_domain=self.domain,
            profile_type=self.profile_type,
            profile=self.profile,
            msg=i.get('msg'),
        )

    @base.require_login
    def POST(self, profile_type, domain):
        self.profile_type = str(profile_type)
        self.domain = str(domain)

        i = web.input()

        domainLib = domainlib.Domain()
        result = domainLib.update(
            profile_type=self.profile_type,
            domain=self.domain,
            data=i,
        )

        if result[0] is True:
            return web.seeother('/profile/domain/%s/%s?msg=PROFILE_UPDATED_SUCCESS' % (self.profile_type, self.domain))
        else:
            return web.seeother('/profile/domain/%s/%s?msg=%s' % (self.profile_type, self.domain, result[1],))


class Create:
    @base.require_global_admin
    @base.require_login
    def GET(self):
        i = web.input()
        return web.render(
            'mysql/domain/create.html',
            msg=i.get('msg'),
        )

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
