# encoding: utf-8

# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings
from libs import languages, iredutils
from libs.pgsql import decorators, admin as adminlib, domain as domainlib

session = web.config.get('_session')


class List:
    @decorators.require_global_admin
    @decorators.require_login
    def GET(self, cur_page=1):
        i = web.input()
        cur_page = int(cur_page)

        if cur_page == 0:
            cur_page == 1

        adminLib = adminlib.Admin()
        result = adminLib.listAccounts(cur_page=cur_page)
        if result[0] is True:
            (total, records) = (result[1]['total'], result[1]['records'])

            # Get list of global admins.
            allGlobalAdmins = []
            qr = adminLib.get_all_global_admins(mail_only=True)
            if qr[0]:
                allGlobalAdmins = qr[1]

            return web.render(
                'pgsql/admin/list.html',
                cur_page=cur_page,
                total=total,
                admins=records,
                allGlobalAdmins=allGlobalAdmins,
                msg=i.get('msg', None),
            )
        else:
            raise web.seeother('/domains?msg=%s' % web.urlquote(result[1]))

    @decorators.require_global_admin
    @decorators.csrf_protected
    @decorators.require_login
    def POST(self):
        i = web.input(_unicode=False, mail=[])

        self.mails = i.get('mail', [])
        self.action = i.get('action', None)
        msg = i.get('msg', None)

        adminLib = adminlib.Admin()

        if self.action == 'delete':
            result = adminLib.delete(mails=self.mails,)
            msg = 'DELETED'
        elif self.action == 'disable':
            result = adminLib.enableOrDisableAccount(accounts=self.mails, active=False,)
            msg = 'DISABLED'
        elif self.action == 'enable':
            result = adminLib.enableOrDisableAccount(accounts=self.mails, active=True,)
            msg = 'ENABLED'
        else:
            result = (False, 'INVALID_ACTION')

        if result[0] is True:
            raise web.seeother('/admins?msg=%s' % msg)
        else:
            raise web.seeother('/admins?msg=?' + web.urlquote(result[1]))


class Profile:
    @decorators.require_login
    def GET(self, profile_type, mail):
        i = web.input()
        self.mail = web.safestr(mail)
        self.profile_type = web.safestr(profile_type)

        if not iredutils.is_email(self.mail):
            raise web.seeother('/admins?msg=INVALID_MAIL')

        if session.get('domainGlobalAdmin') is not True and session.get('username') != self.mail:
            # Don't allow to view/update other admins' profile.
            raise web.seeother('/profile/admin/general/%s?msg=PERMISSION_DENIED' % session.get('username'))

        adminLib = adminlib.Admin()
        result = adminLib.profile(mail=self.mail)

        if result[0] is True:
            domainGlobalAdmin, profile = result[1], result[2]

            # Get all domains.
            self.allDomains = []

            domainLib = domainlib.Domain()
            resultOfAllDomains = domainLib.getAllDomains()
            if resultOfAllDomains[0] is True:
                self.allDomains = resultOfAllDomains[1]

            # Get managed domains.
            self.managedDomains = []

            return web.render(
                'pgsql/admin/profile.html',
                mail=self.mail,
                profile_type=self.profile_type,
                domainGlobalAdmin=domainGlobalAdmin,
                profile=profile,
                languagemaps=languages.get_language_maps(),
                allDomains=self.allDomains,
                min_passwd_length=settings.min_passwd_length,
                max_passwd_length=settings.max_passwd_length,
                msg=i.get('msg'),
            )
        else:
            raise web.seeother('/admins?msg=' + web.urlquote(result[1]))

    @decorators.csrf_protected
    @decorators.require_login
    def POST(self, profile_type, mail):
        self.profile_type = web.safestr(profile_type)
        self.mail = web.safestr(mail)
        i = web.input(domainName=[],)

        if session.get('domainGlobalAdmin') is not True and session.get('username') != self.mail:
            # Don't allow to view/update others' profile.
            raise web.seeother('/profile/admin/general/%s?msg=PERMISSION_DENIED' % session.get('username'))

        adminLib = adminlib.Admin()
        result = adminLib.update(
            profile_type=self.profile_type,
            mail=self.mail,
            data=i,
        )

        if result[0] is True:
            raise web.seeother('/profile/admin/%s/%s?msg=UPDATED' % (self.profile_type, self.mail))
        else:
            raise web.seeother('/profile/admin/%s/%s?msg=%s' % (self.profile_type, self.mail, web.urlquote(result[1]),))


class Create:
    @decorators.require_global_admin
    @decorators.require_login
    def GET(self):
        i = web.input()
        return web.render(
            'pgsql/admin/create.html',
            languagemaps=languages.get_language_maps(),
            default_language=settings.default_language,
            min_passwd_length=settings.min_passwd_length,
            max_passwd_length=settings.max_passwd_length,
            msg=i.get('msg'),
        )

    @decorators.require_global_admin
    @decorators.csrf_protected
    @decorators.require_login
    def POST(self):
        i = web.input()
        self.mail = web.safestr(i.get('mail'))

        adminLib = adminlib.Admin()
        result = adminLib.add(data=i)

        if result[0] is True:
            # Redirect to assign domains.
            raise web.seeother('/profile/admin/general/%s?msg=CREATED' % self.mail)
        else:
            raise web.seeother('/create/admin?msg=' + web.urlquote(result[1]))
