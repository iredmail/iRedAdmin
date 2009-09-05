#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import os, sys
import ldap, ldap.filter
import web
from libs import languages, iredutils
from libs.ldaplib import core, attrs, ldaputils, iredldif

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
    def getLanguageMaps(self):
        # Get available languages.
        self.available_langs = [ web.safestr(v)
                for v in os.listdir(cfg.get('rootdir')+'i18n')
                if v in languages.langmaps
                ]

        # Get language maps.
        self.languagemaps = {}
        [ self.languagemaps.update({i: languages.langmaps[i]})
                for i in self.available_langs
                if i in languages.langmaps
                ]
        return self.languagemaps

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

    # Get admin profile.
    def profile(self, mail):
        self.mail = web.safestr(mail)
        self.dn = ldaputils.convEmailToAdminDN(self.mail)
        try:
            self.admin_profile = self.conn.search_s(
                    self.dn,
                    ldap.SCOPE_BASE,
                    '(&(objectClass=mailAdmin)(mail=%s))' % self.mail,
                    attrs.ADMIN_ATTRS_ALL,
                    )
            return (True, self.admin_profile)
        except Exception, e:
            return (False, str(e))

    def add(self, data):
        self.cn = data.get('cn')
        self.mail = web.safestr(data.get('username')) + '@' + web.safestr(data.get('domain'))

        self.preferredLanguage = web.safestr(data.get('preferredLanguage', 'en_US'))

        # Check password.
        self.newpw = web.safestr(data.get('newpw'))
        self.confirmpw = web.safestr(data.get('confirmpw'))

        result = iredutils.getNewPassword(self.newpw, self.confirmpw)
        if result[0] is True:
            self.passwd = ldaputils.generatePasswd(result[1], pwscheme=cfg.general.get('default_pw_scheme', 'SSHA'))
        else:
            return result

        ldif = iredldif.ldif_mailadmin(
                mail=self.mail,
                passwd=self.passwd,
                cn=self.cn,
                preferredLanguage=self.preferredLanguage,
                )

        self.dn = ldaputils.convEmailToAdminDN(self.mail)

        try:
            self.conn.add_s(self.dn, ldif)
            return (True, 'SUCCESS')
        except ldap.ALREADY_EXISTS:
            return (False, 'ALREADY_EXISTS')
        except Exception, e:
            return (False, str(e))

    # Update admin profile.
    # data: must be a webpy storage object.
    def update(self, profile_type, mail, data):
        self.profile_type = web.safestr(profile_type)
        self.mail = web.safestr(mail)
        self.dn = ldaputils.convEmailToAdminDN(self.mail)

        mod_attrs = []
        if self.profile_type == 'general':
            self.lang = web.safestr(data.get('preferredLanguage', 'en_US'))

            mod_attrs = [
                    (ldap.MOD_REPLACE, 'preferredLanguage', self.lang)
                    ]

            cn = data.get('cn', None)
            if cn is not None:
                mod_attrs += [ ( ldap.MOD_REPLACE, 'cn', cn.encode('utf-8') ) ]
            else:
                # Delete attribute.
                mod_attrs += [ ( ldap.MOD_DELETE, 'cn', None) ]

            try:
                # Modify profiles.
                self.conn.modify_s(self.dn, mod_attrs)
                if session.get('username') == self.mail:
                    web.render = iredutils.setRenderLang(web.render, self.lang, oldlang=session.get('lang'),)
                    session['lang'] = self.lang
                return (True, 'SUCCESS')
            except ldap.LDAPError, e:
                return (False, str(e))

        if self.profile_type == 'password':
            self.cur_passwd = data.get('cur_passwd', None)
            self.newpw = data.get('newpw')
            self.confirmpw = data.get('confirmpw')

            result = iredutils.getNewPassword(self.newpw, self.confirmpw)
            if result[0] is True:
                self.passwd = result[1]
            else:
                return result

            # Change password.
            if self.cur_passwd is None and session.get('domainGlobalAdmin') == 'yes':
                # Reset password without verify old password.
                self.cur_passwd = None
            else:
                self.cur_passwd = str(self.cur_passwd)

            result = self.change_passwd(dn=self.dn, cur_passwd=self.cur_passwd, newpw=self.passwd,)
            if result[0] is True:
                return (True, 'SUCCESS')
            else:
                return result

    def delete(self):
        pass
