# Author: Zhang Huangbin <zhb@iredmail.org>

import web
from controllers import base
from libs import languages
from libs.ldaplib import admin, domain as domainlib, connUtils

cfg = web.iredconfig
session = web.config.get('_session')

#
# Admin related.
#


class List:
    @base.require_global_admin
    @base.require_login
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
            sizelimit=session['pageSizeLimit'],
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
    @base.require_global_admin
    @base.require_login
    def POST(self):
        i = web.input(_unicode=False, mail=[])
        self.mails = i.get('mail', [])
        self.action = i.get('action', None)

        adminLib = admin.Admin()
        if self.action == 'delete':
            result = adminLib.delete(mails=self.mails,)
            msg = 'DELETED_SUCCESS'
        elif self.action == 'disable':
            result = adminLib.enableOrDisableAccount(mails=self.mails, action='disable',)
            msg = 'DISABLED_SUCCESS'
        elif self.action == 'enable':
            result = adminLib.enableOrDisableAccount(mails=self.mails, action='enable',)
            msg = 'ENABLED_SUCCESS'
        else:
            result = (False, 'INVALID_ACTION')
            msg = i.get('msg', None)

        if result[0] is True:
            return web.seeother('/admins?msg=%s' % msg)
        else:
            return web.seeother('/admins?msg=?' + result[1])


class Create:
    @base.require_global_admin
    @base.require_login
    def GET(self):
        i = web.input()
        return web.render('ldap/admin/create.html',
                          languagemaps=languages.getLanguageMaps(),
                          default_language=cfg.general.get('lang', 'en_US'),
                          min_passwd_length=cfg.general.get('min_passwd_length'),
                          max_passwd_length=cfg.general.get('max_passwd_length'),
                          msg=i.get('msg'),
                         )

    @base.require_global_admin
    @base.require_login
    def POST(self):
        i = web.input()
        self.mail = web.safestr(i.get('mail'))

        adminLib = admin.Admin()
        result = adminLib.add(data=i)

        if result[0] is True:
            # Redirect to assign domains.
            return web.seeother('/profile/admin/general/%s?msg=CREATED_SUCCESS' % self.mail)
        else:
            return web.seeother('/create/admin?msg=' + result[1])


class Profile:
    @base.require_login
    def GET(self, profile_type, mail):
        self.mail = web.safestr(mail)
        self.profile_type = web.safestr(profile_type)

        if session.get('domainGlobalAdmin') is not True and session.get('username') != self.mail:
            # Don't allow to view/update other admins' profile.
            return web.seeother('/profile/admin/general/%s?msg=PERMISSION_DENIED' % session.get('username'))

        adminLib = admin.Admin()
        # Get admin profile.
        result = adminLib.profile(self.mail)
        if result[0] is not True:
            return web.seeother('/admins?msg=' + result[1])
        else:
            self.admin_profile = result[1]

        i = web.input()

        if self.profile_type == 'general':
            # Get available languages.
            if result[0] is True:
                ###################
                # Managed domains
                #

                # Check permission.
                #if session.get('domainGlobalAdmin') is not True:
                #    return web.seeother('/profile/admin/general/%s?msg=PERMISSION_DENIED' % self.mail)

                # Get all domains.
                domainLib = domainlib.Domain()
                resultOfAllDomains = domainLib.listAccounts(attrs=['domainName', 'cn', ])
                if resultOfAllDomains[0] is True:
                    self.allDomains = resultOfAllDomains[1]
                else:
                    return resultOfAllDomains

                # Get domains under control.
                resultOfManagedDomains = adminLib.getManagedDomains(mail=self.mail, attrs=['domainName', ])
                if resultOfManagedDomains[0] is True:
                    self.managedDomains = []
                    for d in resultOfManagedDomains[1]:
                        if 'domainName' in d[1].keys():
                            self.managedDomains += d[1].get('domainName')
                else:
                    return resultOfManagedDomains

                return web.render(
                    'ldap/admin/profile.html',
                    mail=self.mail,
                    profile_type=self.profile_type,
                    profile=self.admin_profile,
                    languagemaps=languages.getLanguageMaps(),
                    allDomains=self.allDomains,
                    managedDomains=self.managedDomains,
                    msg=i.get('msg', None),
                )
            else:
                return web.seeother('/profile/admin/%s/%s?msg=%s' % (self.profile_type, self.mail, result[1]))

        elif self.profile_type == 'password':
            return web.render('ldap/admin/profile.html',
                              mail=self.mail,
                              profile_type=self.profile_type,
                              profile=self.admin_profile,
                              min_passwd_length=cfg.general.get('min_passwd_length'),
                              max_passwd_length=cfg.general.get('max_passwd_length'),
                              msg=i.get('msg', None),
                             )

    @base.require_login
    def POST(self, profile_type, mail):
        self.profile_type = web.safestr(profile_type)
        self.mail = web.safestr(mail)
        i = web.input(domainName=[],)

        if session.get('domainGlobalAdmin') is not True and session.get('username') != self.mail:
            # Don't allow to view/update other admins' profile.
            return web.seeother('/profile/admin/general/%s?msg=PERMISSION_DENIED' % session.get('username'))

        adminLib = admin.Admin()
        result = adminLib.update(
                profile_type=self.profile_type,
                mail=self.mail,
                data=i,
                )

        if result[0] is True:
            return web.seeother('/profile/admin/%s/%s?msg=PROFILE_UPDATED_SUCCESS' % (self.profile_type, self.mail))
        else:
            return web.seeother('/profile/admin/%s/%s?msg=%s' % (self.profile_type, self.mail, result[1]))
