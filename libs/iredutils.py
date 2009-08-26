#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import gettext
import os
import web

cfg = web.iredconfig

def setRenderLang(renderInst, lang):
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

    renderInst._lookup.install_gettext_translations(translations)
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
