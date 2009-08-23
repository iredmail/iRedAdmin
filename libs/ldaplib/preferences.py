#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import os
import sys
import ldap
import web
from web import iredconfig as cfg
from libs import languages
from libs.ldaplib import core, attrs, iredutils

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
                session.get('userdn'),
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
        self.new_passwd = data.get('new_passwd')
        self.new_passwd_confirm = data.get('new_passwd_confirm')

        mod_attrs = [
                (ldap.MOD_REPLACE, 'preferredLanguage', self.lang)
                ]
        dn = session.get('userdn')
        self.conn.modify_s(dn, mod_attrs)

        return True
