#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import os
import sys
import ldap
import web
from web import iredconfig as cfg
from libs import languages
from libs.ldaplib import core, attrs, ldaputils

session = web.config.get('_session')

class Preferences(core.LDAPWrap):
    def __del__(self):
        pass

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

    # Update admin profile.
    # data: must be a webpy storage object.
    def update(self, data):
        self.lang = web.safestr(data.get('preferredLanguage', 'en_US'))
        self.cur_passwd = data.get('cur_passwd')
        self.newpw = data.get('newpw')
        self.confirmpw = data.get('confirmpw')

        mod_attrs = [
                (ldap.MOD_REPLACE, 'preferredLanguage', self.lang)
                ]
        self.dn = ldaputils.convEmailToAdminDN(session.get('username'))
        try:
            self.conn.modify_s(self.dn, mod_attrs)
            self.change_passwd(
                    dn=self.dn,
                    cur_passwd=self.cur_passwd,
                    newpw=self.newpw,
                    confirmpw=self.confirmpw,
                    )
            return (True, 'SUCCESS')
        except ldap.LDAPError, e:
            return (False, str(e))
