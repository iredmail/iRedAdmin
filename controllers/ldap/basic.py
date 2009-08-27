#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import web, sys
from libs import __version__, __url_iredadmin_lastest__, iredutils
from libs.ldaplib import core, auth, domain, ldaputils
from controllers.ldap import base

session = web.config.get('_session')
render = web.render

class login:
    def GET(self):
        if session.get('logged') is True:
            web.seeother('/dashboard')
        else:
            i = web.input()
            msg = i.get('msg', None)

            # Show login page.
            return render.login(msg=msg)

    def POST(self):
        # Get username, password.
        i = web.input()

        username = web.safestr(i.get('username').strip())

        # Convert username to ldap dn.
        userdn = ldaputils.convEmailToAdminDN(username)
        if not userdn:
            return render.login(msg='INVALID_USERNAME')

        password = i.get('password').strip()
        save_pass = web.safestr(i.get('save_pass', 'no').strip())

        # Return True if auth success, otherwise return error msg.
        self.auth_result = auth.Auth(userdn, password)

        if self.auth_result == True:
            session['username'] = username
            session['userdn'] = userdn
            session['logged'] = True

            web.config.session_parameters['cookie_name'] = 'iRedAdmin'
            # Session expire when client ip was changed.
            web.config.session_parameters['ignore_change_ip'] = False

            # Session timeout:
            # number of second after a not-updated session will be considered expired
            if save_pass == 'yes':
                # Session timeout (in seconds).
                web.config.session_parameters['timeout'] = 86400    # 24 hours
            else:
                # Expire session when browser closed.
                web.config.session_parameters['timeout'] = 600      # 10 minutes

            # Per-user i18n.
            try:
                adminLib = admin.Admin()
                lang = adminLib.getPreferredLanguage(userdn)
                if lang is not False:
                    web.render = iredutils.setRenderLang(web.render, lang)
                    session['lang'] = lang
            except:
                pass

            web.seeother('/dashboard')
        else:
            session['failedTimes'] += 1
            return render.login(msg=self.auth_result, webmaster=session.get('webmaster'))

class logout:
    def GET(self):
        session.kill()
        web.seeother('/login')

class dashboard:
    @base.protected
    def GET(self):
        from socket import gethostname
        import os
        return render.dashboard(
                version=__version__,
                hostname=gethostname(),
                uptime=iredutils.getServerUptime(),
                loadavg=os.getloadavg(),
                )

class checknew:
    @base.check_global_admin
    @base.protected
    def GET(self):
        import urllib2
        try:
            f = urllib2.urlopen(__url_iredadmin_lastest__)
            info = f.read().strip().split('\n')[:3]
        except Exception, e:
            info = (None, str(e))
        return render.checknew(version=__version__, info=info,)

class dbinit:
    def __init__(self):
        self.dbwrap = core.LDAPWrap(app=web.app, session=session)
