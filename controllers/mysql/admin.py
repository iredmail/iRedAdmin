# encoding: utf-8

# Author: Zhang Huangbin <zhb@iredmail.org>

import web
from libs import languages, iredutils
from libs.mysql import decorators, admin as adminlib, domain as domainlib

cfg = web.iredconfig
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
            (total, records) = (result[1], result[2])

            # Get list of global admins.
            allGlobalAdmins = []
            qr = adminLib.getAllGlobalAdmins()
            if qr[0] is True:
                allGlobalAdmins = qr[1]

            return web.render(
                'mysql/admin/list.html',
                cur_page=cur_page,
                total=total,
                admins=records,
                allGlobalAdmins=allGlobalAdmins,
                msg=i.get('msg', None),
            )
        else:
            return web.seeother('/domains?msg=%s' % result[1])

    @decorators.require_global_admin
    @decorators.require_login
    def POST(self):
        i = web.input(_unicode=False, mail=[])

        self.mails = i.get('mail', [])
        self.action = i.get('action', None)
        msg = i.get('msg', None)

        adminLib = adminlib.Admin()

        if self.action == 'delete':
            result = adminLib.delete(mails=self.mails,)
            msg = 'DELETED_SUCCESS'
        elif self.action == 'disable':
            result = adminLib.enableOrDisableAccount(accounts=self.mails, active=False,)
            msg = 'DISABLED_SUCCESS'
        elif self.action == 'enable':
            result = adminLib.enableOrDisableAccount(accounts=self.mails, active=True,)
            msg = 'ENABLED_SUCCESS'
        else:
            result = (False, 'INVALID_ACTION')

        if result[0] is True:
            return web.seeother('/admins?msg=%s' % msg)
        else:
            return web.seeother('/admins?msg=?' + result[1])

class Profile:
    @decorators.require_login
    def GET(self, profile_type, mail):
        i = web.input()
        self.mail = web.safestr(mail)
        self.profile_type = web.safestr(profile_type)

        if not iredutils.isEmail(self.mail):
            return web.seeother('/admins?msg=INVALID_MAIL')

        if session.get('domainGlobalAdmin') is not True and session.get('username') != self.mail:
            # Don't allow to view/update other admins' profile.
            return web.seeother('/profile/admin/general/%s?msg=PERMISSION_DENIED' % session.get('username'))

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

            qr = adminLib.getManagedDomains(admin=self.mail, domainNameOnly=True, listedOnly=True,)
            if qr[0] is True:
                self.managedDomains += qr[1]

            return web.render(
                'mysql/admin/profile.html',
                mail=self.mail,
                profile_type=self.profile_type,
                domainGlobalAdmin=domainGlobalAdmin,
                profile=profile,
                languagemaps=languages.getLanguageMaps(),
                allDomains=self.allDomains,
                managedDomains=self.managedDomains,
                min_passwd_length=cfg.general.get('min_passwd_length', '0'),
                max_passwd_length=cfg.general.get('max_passwd_length', '0'),
                msg=i.get('msg'),
            )
        else:
            return web.seeother('/admins?msg=' + result[1])


    @decorators.require_login
    def POST(self, profile_type, mail):
        self.profile_type = web.safestr(profile_type)
        self.mail = web.safestr(mail)
        i = web.input(domainName=[],)

        if session.get('domainGlobalAdmin') is not True and session.get('username') != self.mail:
            # Don't allow to view/update others' profile.
            return web.seeother('/profile/admin/general/%s?msg=PERMISSION_DENIED' % session.get('username'))

        adminLib = adminlib.Admin()
        result = adminLib.update(
            profile_type=self.profile_type,
            mail=self.mail,
            data=i,
        )

        if result[0] is True:
            return web.seeother('/profile/admin/%s/%s?msg=PROFILE_UPDATED_SUCCESS' % (self.profile_type, self.mail))
        else:
            return web.seeother('/profile/admin/%s/%s?msg=%s' % (self.profile_type, self.mail, result[1],))


class Create:
    @decorators.require_global_admin
    @decorators.require_login
    def GET(self):
        i = web.input()
        return web.render(
            'mysql/admin/create.html',
            languagemaps=languages.getLanguageMaps(),
            default_language=cfg.general.get('lang', 'en_US'),
            min_passwd_length=cfg.general.get('min_passwd_length'),
            max_passwd_length=cfg.general.get('max_passwd_length'),
            msg=i.get('msg'),
        )

    @decorators.require_global_admin
    @decorators.require_login
    def POST(self):
        i = web.input()
        self.mail = web.safestr(i.get('mail'))

        adminLib = adminlib.Admin()
        result = adminLib.add(data=i)

        if result[0] is True:
            # Redirect to assign domains.
            return web.seeother('/profile/admin/general/%s?msg=CREATED_SUCCESS' % self.mail)
        else:
            return web.seeother('/create/admin?msg=' + result[1])


