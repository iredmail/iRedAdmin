#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import os, sys
import ldap, ldap.filter
import web
from libs import languages
from libs.ldaplib import core, attrs, ldaputils

cfg = web.iredconfig
session = web.config.get('_session')

class Admin(core.LDAPWrap):
    def __del__(self):
        pass

    # Get preferredLanguage.
    def getPreferredLanguage(self, dn):
        dn = ldap.filter.escape_filter_chars(dn)
        self.lang = self.conn.search_s(
                dn,
                ldap.SCOPE_BASE,
                attrlist=['preferredLanguage'],
                )
        if self.lang[0][1].has_key('preferredLanguage'):
            lang = self.lang[0][1]['preferredLanguage'][0]
        else:
            lang = session.get('lang')
        return lang

    # Get available languages.
    def get_langs(self):
        # Get available languages.
        self.available_langs = [ web.safestr(v)
                for v in os.listdir(cfg.get('rootdir')+'i18n')
                if v in languages.langmaps
                ]

        # Get language maps.
        self.langmaps = {}
        [ self.langmaps.update({i: languages.langmaps[i]})
                for i in self.available_langs
                if i in languages.langmaps
                ]

        # Get current language.
        self.cur_lang = self.conn.search_s(
                ldaputils.convEmailToAdminDN(session.get('username')),
                ldap.SCOPE_BASE,
                '(&(objectClass=mailAdmin)(%s=%s))' % (attrs.USER_RDN, session.get('username')),
                ['preferredLanguage'],
                )

        if len(self.cur_lang[0][1]) != 0:
            self.cur_lang = self.cur_lang[0][1]['preferredLanguage'][0]
        else:
            self.cur_lang = session.get('lang')

        return {'cur_lang': self.cur_lang, 'langmaps': self.langmaps}

    # List all admin accounts.
    def list(self):
        filter = attrs.DOMAINADMIN_SEARCH_FILTER
        self.admins = self.conn.search_s(
                self.domainadmin_dn,
                ldap.SCOPE_ONELEVEL,
                filter,
                attrs.DOMAINADMIN_SEARCH_ATTRS,
                )

        return self.admins

    def add(self, admin, passwd, domainGlobalAdmin):
        # msg: {'admin': 'result'}
        msg = {}
        admin = str(admin)
        dn = "mail=" + admin + "," + self.domainadmin_dn
        ldif = iredldif.ldif_mailadmin(admin, passwd, domainGlobalAdmin)

        try:
            # Add object and initialize password.
            self.conn.add_s(dn, ldif)
            self.conn.passwd(dn, passwd, passwd)
            msg[admin] = 'SUCCESS'
        except ldap.ALREADY_EXISTS:
            msg[admin] = 'ALREADY_EXISTS'
        except ldap.LDAPError, e:
            msg[admin] = str(e)

        return msg

    # Update admin profile.
    # data: must be a webpy storage object.
    def update(self, profile_type, mail, data):
        self.profile_type = web.safestr(profile_type)
        self.mail = web.safestr(mail)
        self.dn = ldaputils.convEmailToAdminDN(self.mail)


        if self.profile_type == 'general':
            self.lang = web.safestr(data.get('preferredLanguage', 'en_US'))

            mod_attrs = [
                    (ldap.MOD_REPLACE, 'preferredLanguage', self.lang)
                    ]

            try:
                # Modify profiles.
                self.conn.modify_s(self.dn, mod_attrs)
                return (True, 'SUCCESS')
            except ldap.LDAPError, e:
                return (False, str(e))

        if self.profile_type == 'password':
            self.cur_passwd = data.get('cur_passwd')
            self.newpw = data.get('newpw')
            self.confirmpw = data.get('confirmpw')

            try:
                # Change password.
                self.change_passwd(
                        dn=self.dn,
                        cur_passwd=self.cur_passwd,
                        newpw=self.newpw,
                        confirmpw=self.confirmpw,
                        )
                return (True, 'SUCCESS')
            except ldap.LDAPError, e:
                return (False, str(e))
