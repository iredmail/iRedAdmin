#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import sys
import web
from web import render
from controllers.ldap.basic import dbinit
from controllers.ldap import base
from libs.ldaplib import admin, ldaputils, iredldif

cfg = web.iredconfig
session = web.config.get('_session')

adminLib = admin.Admin()

#
# Admin related.
#
class list(dbinit):
    @base.check_global_admin
    @base.protected
    def GET(self):
        i = web.input()
        self.admins = adminLib.list()
        return render.admins(admins=self.admins, msg=i.get('msg', None))

    # Delete admins.
    @base.check_global_admin
    @base.protected
    def POST(self):
        i = web.input(_unicode=False, mail=[])
        self.mails = i.get('mail', [])
        result = adminLib.delete(mails=self.mails)
        if result[0] is True:
            web.seeother('/admins?msg=DELETE_SUCCESS')
        else:
            web.seeother('/admins?msg=%s' % result[1])

class create(dbinit):
    @base.check_global_admin
    @base.protected
    def GET(self):
        return render.admin_create(
                languagemaps=adminLib.getLanguageMaps(),
                min_passwd_length=cfg.general.get('min_passwd_length'),
                max_passwd_length=cfg.general.get('max_passwd_length'),
                )

    @base.check_global_admin
    @base.protected
    def POST(self):
        i = web.input()
        self.username = web.safestr(i.get('username'))
        self.domain = web.safestr(i.get('domain'))
        self.mail = self.username + '@' + self.domain
        result = adminLib.add(data=i)

        if result[0] is True:
            web.seeother('/profile/admin/general/%s?msg=CREATE_SUCCESS' % self.mail)
        else:
            self.cn = i.get('cn')
            return render.admin_create(
                    username=self.username,
                    domain=self.domain,
                    cn=self.cn,
                    languagemaps=adminLib.getLanguageMaps(),
                    msg=result[1],
                    )

class profile(dbinit):
    @base.protected
    def GET(self, profile_type, mail):
        self.mail = web.safestr(mail)
        self.profile_type = web.safestr(profile_type)

        if session.get('domainGlobalAdmin') != 'yes' and session.get('username') != self.mail:
            # Don't allow to view/update other admins' profile.
            web.seeother('/profile/admin/%s/%s?msg=PERMISSION_DENIED' % ( self.profile_type, session.get('username') ))
        else:
            i = web.input()
            if self.profile_type == 'general':
                # Get admin profile.
                self.profile = adminLib.profile(self.mail)

                # Get available languages.
                if self.profile[0] is True:
                    return render.admin_profile(
                            mail=self.mail,
                            profile_type=self.profile_type,
                            profile=self.profile[1],
                            languagemaps=adminLib.getLanguageMaps(),
                            msg=i.get('msg', None),
                            )
                else:
                    web.seeother('/profile/admin/%s/%s?msg=%s' % (self.profile_type, self.mail, self.profile[1]))
            elif self.profile_type == 'password':
                return render.admin_profile(
                        mail=self.mail,
                        profile_type=self.profile_type,
                        min_passwd_length=cfg.general.get('min_passwd_length'),
                        max_passwd_length=cfg.general.get('max_passwd_length'),
                        msg=i.get('msg', None),
                        )

    @base.protected
    def POST(self, profile_type, mail):
        self.profile_type = web.safestr(profile_type)
        self.mail = web.safestr(mail)
        i = web.input()

        result = adminLib.update(
                profile_type=self.profile_type,
                mail=self.mail,
                data=i,
                )
        if result[0] is True:
            web.seeother('/profile/admin/%s/%s?msg=UPDATE_SUCCESS' % (self.profile_type, self.mail))
        else:
            if self.profile_type == 'general':
                return render.admin_profile(
                        mail=self.mail,
                        profile_type=self.profile_type,
                        languagemaps=adminLib.getLanguageMaps(),
                        msg=result[1],
                        )
            elif self.profile_type == 'password':
                return render.admin_profile(
                        mail=self.mail,
                        profile_type=self.profile_type,
                        min_passwd_length=cfg.general.get('min_passwd_length'),
                        max_passwd_length=cfg.general.get('max_passwd_length'),
                        msg=result[1],
                        )
