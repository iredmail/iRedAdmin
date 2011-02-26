# Author: Zhang Huangbin <zhb@iredmail.org>

import sys
import os
import time
import web
from socket import getfqdn
from urllib import urlencode
from controllers import base
from libs import __url_iredadmin_ldap_latest__, __version__
from libs import iredutils, languages
from libs.ldaplib import auth, admin as adminlib, ldaputils, connUtils, attrs

cfg = web.iredconfig
session = web.config.get('_session')


class Login:
    def GET(self):
        if session.get('logged') is True:
            return web.seeother('/dashboard')
        else:
            i = web.input(_unicode=False)

            # Show login page.
            return web.render('login.html',
                              languagemaps=languages.getLanguageMaps(),
                              webmaster=session.get('webmaster'),
                              msg=i.get('msg'),
                             )

    def POST(self):
        # Get username, password.
        i = web.input(_unicode=False)

        username = web.safestr(i.get('username', '').strip())
        password = i.get('password', '').strip()
        save_pass = web.safestr(i.get('save_pass', 'no').strip())

        if not iredutils.isEmail(username):
            return web.seeother('/login?msg=INVALID_USERNAME')

        if len(password) == 0:
            return web.seeother('/login?msg=EMPTY_PASSWORD')

        # Convert username to ldap dn.
        userdn = ldaputils.convKeywordToDN(username, accountType='admin')

        # Return True if auth success, otherwise return error msg.
        self.auth_result = auth.Auth(cfg.ldap.get('uri', 'ldap://127.0.0.1/'), userdn, password,)

        if self.auth_result is True:
            session['username'] = username
            session['logged'] = True

            # Read preferred language from db.
            adminLib = adminlib.Admin()
            #session['lang'] = adminLib.getPreferredLanguage(userdn) or cfg.general.get('lang', 'en_US')
            adminProfile = adminLib.profile(username)
            if adminProfile[0] is True:
                cn = adminProfile[1][0][1].get('cn', [None])[0]
                lang = adminProfile[1][0][1].get('preferredLanguage', [cfg.general.get('lang', 'en_US')])[0]

                session['cn'] = cn
                session['lang'] = lang
            else:
                pass

            web.config.session_parameters['cookie_name'] = 'iRedAdmin'
            # Session expire when client ip was changed.
            web.config.session_parameters['ignore_change_ip'] = False
            # Don't ignore session expiration.
            web.config.session_parameters['ignore_expiry'] = False

            if save_pass == 'yes':
                # Session timeout (in seconds).
                web.config.session_parameters['timeout'] = 86400    # 24 hours
            else:
                # Expire session when browser closed.
                web.config.session_parameters['timeout'] = 600      # 10 minutes

            web.logger(msg="Login success", event='login',)
            return web.seeother('/dashboard/checknew')
        else:
            session['failedTimes'] += 1
            web.logger(msg="Login failed.", admin=username, event='login', loglevel='error',)
            return web.seeother('/login?msg=%s' % self.auth_result)


class Logout:
    @base.require_login
    def GET(self):
        session.kill()
        return web.seeother('/login')


class Dashboard:
    @base.require_login
    def GET(self, checknew=None):
        i = web.input(_unicode=False,)

        if checknew is not None:
            self.checknew = True
        else:
            self.checknew = False

        # Get network interface related infomation.
        netif_data = {}
        try:
            import netifaces
            ifaces = netifaces.interfaces()
            for iface in ifaces:
                addr = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in addr.keys():
                    data = addr[netifaces.AF_INET][0]
                    try:
                        netif_data[iface] = {'addr': data['addr'], 'netmask': data['netmask'], }
                    except:
                        pass
        except:
            pass

        # Check new version.
        if session.get('domainGlobalAdmin') is True and self.checknew is True:
            try:
                curdate = time.strftime('%Y-%m-%d')
                vars = dict(date=curdate)

                r = web.admindb.select('updatelog', vars=vars, where='date >= $date',)
                if len(r) == 0:
                    urlInfo = {
                        'a': cfg.general.get('webmaster', session.get('username', '')),
                        'v': __version__,
                        'host': getfqdn(),
                    }

                    url = __url_iredadmin_ldap_latest__ + '?' + urlencode(urlInfo)
                    newVersionInfo = iredutils.getNewVersion(url)

                    # Always remove all old records, just keep the last one.
                    web.admindb.delete('updatelog', vars=vars, where='date < $date',)

                    # Insert updating date.
                    web.admindb.insert('updatelog', date=curdate,)
                else:
                    newVersionInfo = (None, )
            except Exception, e:
                newVersionInfo = (False, str(e))
        else:
            newVersionInfo = (None, )

        return web.render(
            'dashboard.html',
            version=__version__,
            hostname=getfqdn(),
            uptime=iredutils.getServerUptime(),
            loadavg=os.getloadavg(),
            netif_data=netif_data,
            newVersionInfo=newVersionInfo,
        )
