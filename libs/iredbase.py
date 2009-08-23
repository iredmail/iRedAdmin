#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby@gmail.com>

'''
init settings
'''

import os, sys, time
import ConfigParser
import gettext

import web
from web.contrib.template import render_jinja

# Directory to be used as the Python egg cache directory.
# Note that the directory specified must exist and be writable by the
# user that the daemon process run as. 
os.environ['PYTHON_EGG_CACHE'] = '/tmp/.iredadmin-eggs'

# init settings.ini to a web.storage 
rootdir = os.path.abspath(os.path.dirname(__file__)) + '/../'
settings = ConfigParser.SafeConfigParser()
settings.read(os.path.join(rootdir, 'settings.ini'))

ctx = web.storage(settings._sections)
cfg = web.iredconfig = web.storage()
for k in ctx: 
    web.iredconfig[k] = web.storage(ctx[k])

del settings
del ctx

web.iredconfig['rootdir'] = rootdir

# init urls
if cfg.general.get('backend') == 'ldap':
    from controllers.ldap.urls import urls
else:
    from controllers.mysql.urls import urls

# init app
app = web.application(urls, globals(), autoreload=True)
web.app = app
web.config.debug = eval(cfg.general.get('debug', 'False'))
lang = cfg.general.get('lang', 'en_US')

web.config.session_parameters['cookie_name'] = 'iRedAdmin'
web.config.session_parameters['cookie_domain'] = None
#web.config.session_parameters['timeout'] = 600     # 10 minutes
web.config.session_parameters['ignore_expiry'] = False
web.config.session_parameters['ignore_change_ip'] = False

# init session
sessionDB = web.database(
        host    = cfg.iredadmin.get('host', 'localhost'),
        port    = int(cfg.iredadmin.get('port', '3306')),
        dbn     = cfg.iredadmin.get('dbn', 'mysql'),
        db      = cfg.iredadmin.get('db', 'iredadmin'),
        user    = cfg.iredadmin.get('user', 'iredadmin'),
        pw      = cfg.iredadmin.get('passwd'),
        )
sessionStore = web.session.DBStore(sessionDB, 'sessions')

session = web.session.Session(app, sessionStore,
        initializer={
            'webmaster': cfg.general.get('admin', 'iredmailsupport@gmail.com'),
            'default_quota': cfg.general.get('default_quota', '1024'),
            'username': None,
            'userdn': None,
            'logged': False,
            'failedTimes': 0,   # Integer.
            'lang': lang,
            }
        )
web.config._session = session

# Init translations.
if lang == 'en_US':
    translations = gettext.NullTranslations()
else:
    try:
        translations = gettext.translation(
                'iredadmin',
                rootdir + 'i18n',
                languages=[lang],
                )
    except IOError:
        translations = gettext.NullTranslations()

# Use JinJa2 template.
tmpldir = rootdir + '/templates/' + \
        cfg.general.get('skin', 'default') +  '/' + \
        cfg.general.get('backend')

# init render
def set_render(tmpl_dir):
    r = render_jinja(
            tmpl_dir,                           # template dir.
            extensions = ['jinja2.ext.i18n'],   # Jinja2 extensions.
            encoding = 'utf-8',                 # Encoding.
            globals = {
                'skin': cfg.general.get('skin', 'default'), # Used for static files.
                'session': web.config._session,  # Used for session.
                'ctx': web.ctx,                  # Used to get 'homepath'.
                },
            )
    r._lookup.install_gettext_translations(translations)
    return r

render = set_render(tmpldir)
web.render = render

def notfound():
    return web.notfound(render.pageNotFound())
