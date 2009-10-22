#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

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

import web, sys
from libs import __version__, __url_iredadmin_lastest__, iredutils
from libs.ldaplib import core, admin, auth, domain, ldaputils
from controllers.ldap import base

cfg = web.iredconfig
session = web.config.get('_session')
render = web.render

class login:
    def GET(self):
        if session.get('logged') is True:
            web.seeother('/dashboard')
        else:
            i = web.input()

            adminLib = admin.Admin()
            cur_lang = i.get('lang', cfg.general.get('lang', 'en_US'))
            if cur_lang is not None:
                session['lang'] = cur_lang

            # Show login page.
            return render.login(
                    cur_lang=cur_lang,
                    languagemaps=adminLib.getLanguageMaps(),
                    msg=i.get('msg'),
                    )

    def POST(self):
        # Get username, password.
        i = web.input()

        username = web.safestr(i.get('username').strip())
        password = i.get('password').strip()
        save_pass = web.safestr(i.get('save_pass', 'no').strip())

        if len(username) == 0 or len(password) == 0:
            return render.login(msg='EMPTY_USER_PW')

        # Convert username to ldap dn.
        userdn = ldaputils.convEmailToAdminDN(username)

        # Return True if auth success, otherwise return error msg.
        self.auth_result = auth.Auth(userdn, password)

        if self.auth_result == True:
            session['username'] = username
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
            return render.login(msg=self.auth_result, webmaster=session.get('webmaster'))

class logout:
    def GET(self):
        session.kill()
        web.seeother('/login')

class dashboard:
    @base.protected
    def GET(self):
        from socket import getfqdn
        import os
        try:
            import netifaces
            ifaces = netifaces.interfaces()
            netif_data = {}
            for i in ifaces:
                addr = netifaces.ifaddresses(i)
                if addr.has_key(netifaces.AF_INET):
                    data = addr[netifaces.AF_INET][0]
                    netif_data[i] = {'addr': data['addr'], 'netmask': data['netmask'],}
        except:
            netif_data = None
        return render.dashboard(
                version=__version__,
                hostname=getfqdn(),
                uptime=iredutils.getServerUptime(),
                loadavg=os.getloadavg(),
                netif_data=netif_data,
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
