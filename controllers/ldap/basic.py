# Author: Zhang Huangbin <zhb@iredmail.org>

import os
import time
import ldap
import web
from socket import getfqdn
from urllib import urlencode
from libs import __url_latest_ose__, __version_ose__, __no__, __id__
from libs import iredutils, languages
from libs.ldaplib import auth, decorators, admin as adminlib, ldaputils


cfg = web.iredconfig
session = web.config.get('_session')


class Login:
    def GET(self):
        if session.get('logged') is False:
            i = web.input(_unicode=False)

            # Show login page.
            return web.render('login.html',
                              languagemaps=languages.getLanguageMaps(),
                              webmaster=session.get('webmaster'),
                              msg=i.get('msg'),
                             )
        else:
            raise web.seeother('/dashboard')

    def POST(self):
        # Get username, password.
        i = web.input(_unicode=False)

        # Verify bind_dn & bind_pw.
        try:
            # Get LDAP URI.
            uri = cfg.ldap.get('uri')

            # Detect STARTTLS support.
            if uri.startswith('ldaps://'):
                starttls = True
            else:
                starttls = False

            # Set necessary option for STARTTLS.
            if starttls:
                ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

            # Initialize connection.
            conn = ldap.initialize(uri)

            # Set LDAP protocol version: LDAP v3.
            conn.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)

            if starttls:
                conn.set_option(ldap.OPT_X_TLS, ldap.OPT_X_TLS_DEMAND)

            # synchronous bind.
            conn.bind_s(cfg.ldap.get('bind_dn'), cfg.ldap.get('bind_pw'))
            conn.unbind_s()
        except (ldap.INVALID_CREDENTIALS):
            raise web.seeother('/login?msg=vmailadmin_INVALID_CREDENTIALS')
        except Exception, e:
            raise web.seeother('/login?msg=%s' % web.safestr(e))

        username = web.safestr(i.get('username', '').strip())
        password = i.get('password', '').strip()
        save_pass = web.safestr(i.get('save_pass', 'no').strip())

        if not iredutils.isEmail(username):
            raise web.seeother('/login?msg=INVALID_USERNAME')

        if not password:
            raise web.seeother('/login?msg=EMPTY_PASSWORD')

        # Convert username to ldap dn.
        userdn = ldaputils.convKeywordToDN(username, accountType='admin')
        if userdn[0] is False:
            raise web.seeother('/login?msg=%s' % userdn[1])

        # Return True if auth success, otherwise return error msg.
        qr_admin_auth = auth.Auth(cfg.ldap.get('uri', 'ldap://127.0.0.1/'), userdn, password,)

        if qr_admin_auth is True:
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

            web.config.session_parameters['cookie_name'] = 'iRedAdmin-Pro'
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
            raise web.seeother('/dashboard/checknew')
        else:
            session['failedTimes'] += 1
            web.logger(msg="Login failed.", admin=username, event='login', loglevel='error',)
            raise web.seeother('/login?msg=%s' % qr_admin_auth)


class Logout:
    @decorators.require_login
    def GET(self):
        session.kill()
        raise web.seeother('/login')


class Dashboard:
    @decorators.require_login
    def GET(self, checknew=False):
        if checknew:
            checknew = True

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
                    except Exception:
                        pass
        except Exception:
            pass

        # Check new version.
        newVersionInfo = (None, )
        if session.get('domainGlobalAdmin') is True and checknew is True:
            try:
                curdate = time.strftime('%Y-%m-%d')
                vars = dict(date=curdate)

                r = web.admindb.select('updatelog', vars=vars, where='date >= $date',)
                if len(r) == 0:
                    urlInfo = {
                        'a': cfg.general.get('webmaster', session.get('username', '')),
                        'v': __version_ose__,
                        'o': __no__,
                        'f': __id__,
                        'host': getfqdn(),
                        'backend': cfg.general.get('backend', ''),
                    }

                    url = __url_latest_ose__ + '?' + urlencode(urlInfo)
                    newVersionInfo = iredutils.getNewVersion(url)

                    # Always remove all old records, just keep the last one.
                    web.admindb.delete('updatelog', vars=vars, where='date < $date',)

                    # Insert updating date.
                    web.admindb.insert('updatelog', date=curdate,)
            except Exception, e:
                newVersionInfo = (False, str(e))

        return web.render(
            'dashboard.html',
            version=__version_ose__,
            hostname=getfqdn(),
            uptime=iredutils.getServerUptime(),
            loadavg=os.getloadavg(),
            netif_data=netif_data,
            newVersionInfo=newVersionInfo,
        )
