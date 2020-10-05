# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings

from libs import __version__
from libs import iredutils, sysinfo
from libs.logger import log_activity

from libs.sqllib import SQLWrap, auth, decorators
from libs.sqllib import admin as sql_lib_admin

session = web.config.get('_session')


class Login:
    def GET(self):
        if not session.get('logged'):
            form = web.input(_unicode=False)

            if not iredutils.is_allowed_admin_login_ip(client_ip=web.ctx.ip):
                return web.render('error_without_login.html',
                                  error='NOT_ALLOWED_IP')

            # Show login page.
            return web.render('login.html',
                              languagemaps=iredutils.get_language_maps(),
                              msg=form.get('msg'))
        else:
            if settings.REDIRECT_TO_DOMAIN_LIST_AFTER_LOGIN:
                raise web.seeother('/domains')
            else:
                raise web.seeother('/dashboard')

    def POST(self):
        # Get username, password.
        form = web.input(_unicode=False)

        username = form.get('username', '').strip().lower()
        password = str(form.get('password', '').strip())

        # Auth as domain admin
        _wrap = SQLWrap()
        conn = _wrap.conn

        auth_result = auth.auth(conn=conn,
                                username=username,
                                password=password,
                                account_type='admin')

        if auth_result[0] is True:
            log_activity(msg="Admin login success", event='login')

            # Save selected language
            selected_language = str(form.get('lang', '')).strip()
            if selected_language != web.ctx.lang and \
               selected_language in iredutils.get_language_maps():
                session['lang'] = selected_language

            account_settings = auth_result[1].get('account_settings', {})
            if (not session.get('is_global_admin')) and 'create_new_domains' in account_settings:
                session['create_new_domains'] = True

            for k in ['disable_viewing_mail_log',
                      'disable_managing_quarantined_mails']:
                if account_settings.get(k) == 'yes':
                    session[k] = True

            if settings.REDIRECT_TO_DOMAIN_LIST_AFTER_LOGIN:
                raise web.seeother('/domains')
            else:
                raise web.seeother('/dashboard?checknew')
        else:
            raise web.seeother('/login?msg=INVALID_CREDENTIALS')


class Logout:
    def GET(self):
        try:
            session.kill()
        except:
            pass

        raise web.seeother('/login')


class Dashboard:
    @decorators.require_global_admin
    def GET(self):
        form = web.input(_unicode=False)
        _check_new_version = ('checknew' in form)

        # Check new version.
        if session.get('is_global_admin') and _check_new_version:
            (_status, _info) = sysinfo.check_new_version()
            session['new_version_available'] = _status
            if _status:
                session['new_version'] = _info
            else:
                session['new_version_check_error'] = _info

        # Get numbers of domains, users, aliases.
        num_existing_domains = 0
        num_existing_users = 0

        _wrap = SQLWrap()
        conn = _wrap.conn

        try:
            num_existing_domains = sql_lib_admin.num_managed_domains(conn=conn)
            num_existing_users = sql_lib_admin.num_managed_users(conn=conn)
        except:
            pass

        # Get numbers of existing messages and quota bytes.
        # Set None as default, so that it's easy to detect them in Jinja2 template.
        total_messages = None
        total_bytes = None
        if session.get('is_global_admin'):
            if settings.SHOW_USED_QUOTA:
                try:
                    qr = sql_lib_admin.sum_all_used_quota(conn=conn)
                    total_messages = qr['messages']
                    total_bytes = qr['bytes']
                except:
                    pass

        return web.render(
            'dashboard.html',
            version=__version__,
            iredmail_version=sysinfo.get_iredmail_version(),
            hostname=sysinfo.get_hostname(),
            uptime=sysinfo.get_server_uptime(),
            loadavg=sysinfo.get_system_load_average(),
            netif_data=sysinfo.get_nic_info(),
            # number of existing accounts
            num_existing_domains=num_existing_domains,
            num_existing_users=num_existing_users,
            total_messages=total_messages,
            total_bytes=total_bytes,
        )
