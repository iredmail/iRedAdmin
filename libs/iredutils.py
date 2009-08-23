#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import gettext
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
