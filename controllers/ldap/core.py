#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import web, sys
from libs.ldaplib import core, auth, domain, iredutils
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
        password = i.get('password').strip()
        save_pass = web.safestr(i.get('save_pass', 'no').strip())

        # Convert email to ldap dn.
        userdn = iredutils.convEmailToAdminDN(username)

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

            web.seeother('/dashboard')
        else:
            session['failedTimes'] += 1
            return render.login(msg=self.auth_result, sysadmin=session.get('webmaster', ''))

class logout:
    def GET(self):
        session.kill()
        web.seeother('/login')

class dashboard:
    @base.protected
    def GET(self):
        return render.dashboard()

class dbinit:
    def __init__(self):
        self.dbwrap = core.LDAPWrap(app=web.app, session=session)
        self.domain = domain.Domain()
