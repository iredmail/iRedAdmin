#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby@gmail.com>

#---------------------------------------------------------------------
# This file is part of iRedAdmin-OSE, which is official web-based admin
# panel (Open Source Edition) for iRedMail.
#
# iRedMail is an open source mail server solution for Red Hat(R)
# Enterprise Linux, CentOS, Debian and Ubuntu.
#
# iRedAdmin-OSE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# iRedAdmin-OSE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with iRedAdmin-OSE.  If not, see <http://www.gnu.org/licenses/>.
#---------------------------------------------------------------------

# init settings

import os, sys
import ConfigParser

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

web.config.session_parameters['cookie_name'] = 'iRedAdmin-OSE'
web.config.session_parameters['cookie_domain'] = None
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
            'webmaster': cfg.general.get('webmaster'),
            'username': None,
            'logged': False,
            'failedTimes': 0,   # Integer.
            'lang': lang,
            'pagesizelimit': 30,
            }
        )
web.config._session = session

# Use JinJa2 template.
tmpldir = rootdir + '/templates/' + \
        cfg.general.get('skin', 'default') +  '/' + \
        cfg.general.get('backend')

# Object used to stored all translations.
cfg.allTranslations = web.storage()

import iredutils

# Load i18n hook.
app.add_processor(web.loadhook(iredutils.i18n_loadhook))

# init render
render = render_jinja(
        tmpldir,                           # template dir.
        encoding = 'utf-8',                 # Encoding.
        )

# Add/override global functions.
render._lookup.globals.update(
        skin=cfg.general.get('skin', 'default'), # Used for static files.
        session=web.config._session,  # Used for session.
        ctx=web.ctx,                  # Used to get 'homepath'.
        _=iredutils.ired_gettext,     # Override _() which provided by Jinja2.
        #gettext=iredutils.ired_gettext,
        #ngettext=iredutils.ired_gettext,
        )

# Add/override custom Jinja filters.
render._lookup.filters.update(
        filesizeformat=iredutils.filesizeformat,
        )

def notfound():
    return web.notfound(render.error404())

app.notfound = notfound
web.render = render
