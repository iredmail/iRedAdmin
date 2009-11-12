#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

#---------------------------------------------------------------------
# This file is part of iRedAdmin-OSE, which is official web-based admin
# panel (Open Source Edition) for iRedMail.
#
# iRedMail is an open source mail server solution for Red Hat(R)
# Enterprise Linux, CentOS, Debian and Ubuntu.
#
# iRedAdmin-OSE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# iRedAdmin-OSE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with iRedAdmin-OSE.  If not, see <http://www.gnu.org/licenses/>.
#---------------------------------------------------------------------

import sys
import web
from web import render
from controllers.ldap.basic import dbinit
from controllers import base
from libs.ldaplib import admin, ldaputils, iredldif

cfg = web.iredconfig
session = web.config.get('_session')

adminLib = admin.Admin()

#
# Admin related.
#
class list(dbinit):
    @base.require_global_admin
    @base.require_login
    def GET(self):
        i = web.input()
        self.admins = adminLib.list()
        return render.admins(admins=self.admins, msg=i.get('msg', None))

    # Delete, disable, enable admin accounts.
    @base.require_global_admin
    @base.require_login
    def POST(self):
        i = web.input(_unicode=False, mail=[])
        self.mails = i.get('mail', [])
        if i.has_key('delete'):
            result = adminLib.delete(mails=self.mails,)
            msg = 'DELETED_SUCCESS'
        elif i.has_key('disable'):
            result = adminLib.enableOrDisableAccount(mails=self.mails, value='disabled',)
            msg = 'DISABLED_SUCCESS'
        elif i.has_key('enable'):
            result = adminLib.enableOrDisableAccount(mails=self.mails, value='active',)
            msg = 'ENABLED_SUCCESS'
        else:
            msg = i.get('msg', None)

        if result[0] is True:
            web.seeother('/admins?' + 'msg=' + msg)
        else:
            web.seeother('/admins?' + result[1])

class create(dbinit):
    @base.require_global_admin
    @base.require_login
    def GET(self):
        return render.admin_create(
                languagemaps=adminLib.getLanguageMaps(),
                min_passwd_length=cfg.general.get('min_passwd_length'),
                max_passwd_length=cfg.general.get('max_passwd_length'),
                )

    @base.require_global_admin
    @base.require_login
    def POST(self):
        i = web.input()
        self.username = web.safestr(i.get('username'))
        self.domain = web.safestr(i.get('domain'))
        self.mail = self.username + '@' + self.domain
        result = adminLib.add(data=i)

        if result[0] is True:
            web.seeother('/profile/admin/general/%s?msg=CREATED_SUCCESS' % self.mail)
        else:
            web.seeother('/create/admin?msg=' + result[1])

class profile(dbinit):
    @base.require_login
    def GET(self, profile_type, mail):
        self.mail = web.safestr(mail)
        self.profile_type = web.safestr(profile_type)

        if session.get('domainGlobalAdmin') != 'yes' and session.get('username') != self.mail:
            # Don't allow to view/update other admins' profile.
            web.seeother('/profile/admin/general/%s?msg=PERMISSION_DENIED' % session.get('username'))

        # Get admin profile.
        result = adminLib.profile(self.mail)
        if result[0] is not True:
            web.seeother('/admins?' + result[1])
        else:
            self.admin_profile = result[1]

        i = web.input()

        if self.profile_type == 'general':
            # Get admin profile.
            result = adminLib.profile(self.mail)

            # Get available languages.
            if result[0] is True:
                return render.admin_profile(
                        mail=self.mail,
                        profile_type=self.profile_type,
                        profile=self.admin_profile,
                        languagemaps=adminLib.getLanguageMaps(),
                        msg=i.get('msg', None),
                        )
            else:
                web.seeother('/profile/admin/%s/%s?' % (self.profile_type, self.mail) + result[1])
        elif self.profile_type == 'password':
            return render.admin_profile(
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
        i = web.input()

        if session.get('domainGlobalAdmin') != 'yes' and session.get('username') != self.mail:
            # Don't allow to view/update other admins' profile.
            web.seeother('/profile/admin/general/%s?msg=PERMISSION_DENIED' % session.get('username'))

        result = adminLib.update(
                profile_type=self.profile_type,
                mail=self.mail,
                data=i,
                )
        if result[0] is True:
            web.seeother('/profile/admin/%s/%s?msg=PROFILE_UPDATED_SUCCESS' % (self.profile_type, self.mail))
        else:
            web.seeother('/profile/admin/%s/%s?' % (self.profile_type, self.mail) + result[1])
