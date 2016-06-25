# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings
from libs import languages
from libs.ldaplib import decorators, admin, domain as domainlib, connUtils

session = web.config.get('_session')

#
# Admin related.
#
class List:
    @decorators.require_global_admin
    @decorators.require_login
    def GET(self, cur_page=1):
        i = web.input()
        cur_page = int(cur_page)

        if cur_page == 0:
            cur_page == 1

        adminLib = admin.Admin()
        result = adminLib.listAccounts()

        connutils = connUtils.Utils()
        sl = connutils.getSizelimitFromAccountLists(
            result[1],
            curPage=cur_page,
            sizelimit=settings.PAGE_SIZE_LIMIT,
        )

        if cur_page > sl.get('totalPages', 0):
            cur_page = sl.get('totalPages', 0)

        return web.render(
            'ldap/admin/list.html',
            cur_page=cur_page,
            total=sl.get('totalAccounts'),
            admins=sl.get('accountList'),
            msg=i.get('msg', None),
        )

    # Delete, disable, enable admin accounts.
    @decorators.require_global_admin
    @decorators.csrf_protected
    @decorators.require_login
    def POST(self):
        i = web.input(_unicode=False, mail=[])
        self.mails = i.get('mail', [])
        self.action = i.get('action', None)

        adminLib = admin.Admin()
        if self.action == 'delete':
            result = adminLib.delete(mails=self.mails,)
            msg = 'DELETED'
        elif self.action == 'disable':
            result = adminLib.enableOrDisableAccount(mails=self.mails, action='disable',)
            msg = 'DISABLED'
        elif self.action == 'enable':
            result = adminLib.enableOrDisableAccount(mails=self.mails, action='enable',)
            msg = 'ENABLED'
        else:
            result = (False, 'INVALID_ACTION')
            msg = i.get('msg', None)

        if result[0] is True:
            raise web.seeother('/admins?msg=%s' % msg)
        else:
            raise web.seeother('/admins?msg=' + result[1])


class Create:
    @decorators.require_global_admin
    @decorators.require_login
    def GET(self):
        i = web.input()
        return web.render('ldap/admin/create.html',
                          languagemaps=languages.get_language_maps(),
                          default_language=settings.default_language,
                          min_passwd_length=settings.min_passwd_length,
                          max_passwd_length=settings.max_passwd_length,
                          msg=i.get('msg'))

    @decorators.require_global_admin
    @decorators.csrf_protected
    @decorators.require_login
    def POST(self):
        i = web.input()
        self.mail = web.safestr(i.get('mail'))

        adminLib = admin.Admin()
        result = adminLib.add(data=i)

        if result[0] is True:
            # Redirect to assign domains.
            raise web.seeother('/profile/admin/general/%s?msg=CREATED' % self.mail)
        else:
            raise web.seeother('/create/admin?msg=' + result[1])


class Profile:
    @decorators.require_login
    def GET(self, profile_type, mail):
        self.mail = web.safestr(mail)
        self.profile_type = web.safestr(profile_type)

        if session.get('domainGlobalAdmin') is not True and session.get('username') != self.mail:
            # Don't allow to view/update other admins' profile.
            raise web.seeother('/profile/admin/general/%s?msg=PERMISSION_DENIED' % session.get('username'))

        # Get admin profile.
        adminLib = admin.Admin()
        result = adminLib.profile(self.mail)
        if result[0] is not True:
            raise web.seeother('/admins?msg=' + result[1])
        else:
            self.admin_profile = result[1]

        i = web.input()

        if self.profile_type == 'general':
            # Get available languages.
            if result[0] is True:
                ###################
                # Managed domains
                #

                # Get all domains.
                domainLib = domainlib.Domain()
                resultOfAllDomains = domainLib.listAccounts(attrs=['domainName', 'cn', ])
                if resultOfAllDomains[0] is True:
                    self.allDomains = resultOfAllDomains[1]
                else:
                    return resultOfAllDomains

                return web.render(
                    'ldap/admin/profile.html',
                    mail=self.mail,
                    profile_type=self.profile_type,
                    profile=self.admin_profile,
                    languagemaps=languages.get_language_maps(),
                    allDomains=self.allDomains,
                    msg=i.get('msg', None),
                )
            else:
                raise web.seeother('/profile/admin/%s/%s?msg=%s' % (self.profile_type, self.mail, result[1]))

        elif self.profile_type == 'password':
            return web.render('ldap/admin/profile.html',
                              mail=self.mail,
                              profile_type=self.profile_type,
                              profile=self.admin_profile,
                              min_passwd_length=settings.min_passwd_length,
                              max_passwd_length=settings.max_passwd_length,
                              msg=i.get('msg', None))

    @decorators.csrf_protected
    @decorators.require_login
    def POST(self, profile_type, mail):
        self.profile_type = web.safestr(profile_type)
        self.mail = web.safestr(mail)
        i = web.input(domainName=[],)

        if session.get('domainGlobalAdmin') is not True and session.get('username') != self.mail:
            # Don't allow to view/update other admins' profile.
            raise web.seeother('/profile/admin/general/%s?msg=PERMISSION_DENIED' % session.get('username'))

        adminLib = admin.Admin()
        result = adminLib.update(profile_type=self.profile_type,
                                 mail=self.mail,
                                 data=i)

        if result[0] is True:
            raise web.seeother('/profile/admin/%s/%s?msg=UPDATED' % (self.profile_type, self.mail))
        else:
            raise web.seeother('/profile/admin/%s/%s?msg=%s' % (self.profile_type, self.mail, result[1]))
