#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import web
from web import render
from controllers.ldap import base
from controllers.ldap.basic import dbinit
from libs.ldaplib import admin, preferences

session = web.config.get('_session')

adminLib = admin.Admin()
prefLib = preferences.Preferences()

#
# Admin related.
#
class list(dbinit):
    @base.check_global_admin
    @base.protected
    def GET(self):
        self.admins = adminLib.list()
        return render.admins(admins=self.admins)

    @base.check_global_admin
    @base.protected
    def POST(self):
        i = web.input(dn=[])

        # Post method: add, delete.
        action = i.get('action', None)

        if action == 'add':
            # Get admin list (python list obj).
            admin = i.get('admin', None)
            passwd = i.get('passwd', None)
            domainGlobalAdmin = i.get('domainGlobalAdmin', 'no')

            if admin is not None and passwd is not None:
                # Try to add it.
                results = self.dbwrap.admin_add(admin, passwd, domainGlobalAdmin)

                # List admins.
                self.admins = adminLib.list()
                return render.admins(admins=self.admins, msg=results)
            else:
                # Show system message.
                self.admins = adminLib.list()
                return render.admins(admins=self.admins, msg='NO_DOMAIN')
        elif action == 'delete':
            dn = i.get('dn', [])

            if len(dn) >= 1:
                # Delete dn(s).
                results = self.dbwrap.delete_dn(dn)

                # List admins.
                self.admins = adminLib.list()
                return render.admins(admins=self.admins, msg=results)
            else:
                # Show system message.
                return render.admins()
        else:
            return render.admins()

class add(dbinit):
    @base.check_global_admin
    @base.protected
    def GET(self):
        return render.admin_add()

class profile(dbinit):
    @base.protected
    def GET(self):
        self.langs = prefLib.get_langs()

        return render.admin_profile(
                cur_lang=self.langs.pop('cur_lang'),
                langmaps=self.langs.pop('langmaps'),
                msg=None,
                )

    @base.protected
    def POST(self):
        # Get passwords.
        i = web.input()
        result = prefLib.update(i)
        self.langs = prefLib.get_langs()

        cur_lang = self.langs.pop('cur_lang')
        if result is True:
            msg = 'SUCCESS'
            web.render = iredutils.setRenderLang(web.render, cur_lang, oldlang=session.get('lang'),)
        else:
            msg = result

        return render.admin_profile(
                cur_lang=cur_lang,
                langmaps=self.langs.pop('langmaps'),
                msg=msg,
                )
