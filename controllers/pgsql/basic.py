# Author: Zhang Huangbin <zhb@iredmail.org>

import time
from socket import getfqdn
from urllib import urlencode
import web
import settings
from libs import __url_latest_ose__, __version_ose__
from libs import iredutils, languages
from libs.pgsql import core, decorators


session = web.config.get('_session')


class Login:
    def GET(self):
        if session.get('logged') is False:
            i = web.input(_unicode=False)

            # Show login page.
            return web.render(
                'login.html',
                languagemaps=languages.get_language_maps(),
                msg=i.get('msg'),
            )
        else:
            raise web.seeother('/dashboard')

    def POST(self):
        # Get username, password.
        i = web.input(_unicode=False)

        username = web.safestr(i.get('username').strip()).lower()
        password = str(i.get('password').strip())
        save_pass = web.safestr(i.get('save_pass', 'no').strip())

        auth = core.Auth()
        auth_result = auth.auth(username=username, password=password)

        if auth_result[0] is True:
            # Config session data.
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

            # Save selected language
            selected_language = str(i.get('lang', '')).strip()
            if selected_language != web.ctx.lang and \
               selected_language in languages.get_language_maps():
                session['lang'] = selected_language

            raise web.seeother('/dashboard/checknew')
        else:
            session['failed_times'] += 1
            web.logger(msg="Login failed.", admin=username, event='login', loglevel='error',)
            raise web.seeother('/login?msg=%s' % web.urlquote(auth_result[1]))


class Logout:
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
                    except:
                        pass
        except:
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
                        'v': __version_ose__,
                        'lang': settings.default_language,
                        'host': getfqdn(),
                        'backend': settings.backend,
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
            iredmail_version=iredutils.get_iredmail_version(),
            hostname=getfqdn(),
            uptime=iredutils.get_server_uptime(),
            loadavg=iredutils.get_system_load_average(),
            netif_data=netif_data,
            newVersionInfo=newVersionInfo,
        )
