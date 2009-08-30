#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import gettext
import os
import web

cfg = web.iredconfig

def get_translation(lang):
    # Init translations.
    if lang == 'en_US':
        translations = gettext.NullTranslations()
    else:
        try:
            translations = gettext.translation(
                    'iredadmin',
                    cfg['rootdir'] + 'i18n',
                    languages=[lang],
                    )
        except IOError:
            translations = gettext.NullTranslations()
    return translations

def setRenderLang(renderInst, lang, oldlang=None):
    if oldlang is not None:
        old_translation = get_translation(oldlang)
        renderInst._lookup.uninstall_gettext_translations(old_translation)

    new_translations = get_translation(lang)
    renderInst._lookup.install_gettext_translations(new_translations)
    return renderInst

def notfound():
    return web.notfound(render.pageNotFound())

def getServerUptime():
     try:
         # Works on Linux.
         f = open( "/proc/uptime" )
         contents = f.read().split()
         f.close()
     except:
        return None

     total_seconds = float(contents[0])

     MINUTE  = 60
     HOUR    = MINUTE * 60
     DAY     = HOUR * 24

     # Get the days, hours, minutes.
     days    = int( total_seconds / DAY )
     hours   = int( ( total_seconds % DAY ) / HOUR )
     minutes = int( ( total_seconds % HOUR ) / MINUTE )
     seconds = int( total_seconds % MINUTE )

     return (days, hours, minutes)
