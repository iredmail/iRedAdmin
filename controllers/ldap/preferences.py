#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import sys
import web
from web import render
from controllers.ldap import base
from controllers.ldap.basic import dbinit
from libs import iredutils
from libs.ldaplib import preferences

session = web.config.get('_session')

prefLib = preferences.Preferences()

class Preferences:
    @base.protected
    def GET(self):
        self.langs = prefLib.get_langs()

        return render.preferences(
                cur_lang=self.langs.pop('cur_lang'),
                langmaps=self.langs.pop('langmaps'),
                msg=None,
                )

    @base.protected
    def POST(self):
        # Get passwords.
        i = web.input()
        self.result = prefLib.update(i)
        self.langs = prefLib.get_langs()

        cur_lang = self.langs.pop('cur_lang')
        if self.result is True:
            msg = 'SUCCESS'
            web.render = iredutils.setRenderLang(web.render, cur_lang, oldlang=session.get('lang'),)
        else:
            msg = self.result

        return render.preferences(
                cur_lang=cur_lang,
                langmaps=self.langs.pop('langmaps'),
                msg=msg,
                )
