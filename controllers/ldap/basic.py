# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings

from libs import __version__
from libs import iredutils, sysinfo
from libs.l10n import TIMEZONES
from libs.logger import logger, log_activity
from libs.ldaplib.core import LDAPWrap
from libs.ldaplib import auth, decorators
from libs.ldaplib import admin as ldap_lib_admin
from libs.ldaplib import user as ldap_lib_user
from libs.ldaplib import general as ldap_lib_general

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
                              webmaster=session.get('webmaster'),
                              msg=form.get('msg'))
        else:
            if settings.REDIRECT_TO_DOMAIN_LIST_AFTER_LOGIN:
                raise web.seeother('/domains')
            else:
                raise web.seeother('/dashboard')

    def POST(self):
        # Get username, password.
        form = web.input(_unicode=False)

        username = web.safestr(form.get('username', '').strip()).lower()
        password = form.get('password', '').strip()

        if not iredutils.is_email(username):
            raise web.seeother('/login?msg=INVALID_USERNAME')

        if not password:
            raise web.seeother('/login?msg=EMPTY_PASSWORD')

        domain = username.split('@', 1)[-1]

        _wrap = LDAPWrap()
        conn = _wrap.conn

        # Check whether it's a mail user with admin privilege.
        qr_user_auth = auth.login_auth(username=username,
                                       password=password,
                                       account_type='user',
                                       conn=conn)

        qr_admin_auth = (False, 'INVALID_CREDENTIALS')
        if not qr_user_auth[0]:
            # Verify admin account under 'o=domainAdmins'.
            qr_admin_auth = auth.login_auth(username=username,
                                            password=password,
                                            account_type='admin',
                                            conn=conn)

            if not qr_admin_auth[0]:
                session['failed_times'] += 1
                logger.warning("Web login failed: client_address={}, username={}".format(web.ctx.ip, username))
                log_activity(msg="Login failed.", admin=username, event='login', loglevel='error')
                raise web.seeother('/login?msg=INVALID_CREDENTIALS')

        session['username'] = username

        web.config.session_parameters['cookie_name'] = 'iRedAdmin'
        web.config.session_parameters['ignore_expiry'] = False
        web.config.session_parameters['ignore_change_ip'] = settings.SESSION_IGNORE_CHANGE_IP

        _attrs = ['preferredLanguage', 'accountSetting', 'disabledService']
        # Read preferred language from LDAP
        if qr_admin_auth[0]:
            logger.info("Admin login success: username={}, client_address={}".format(username, web.ctx.ip))
            log_activity(msg="Admin login success", event='login')

            if not session.get('timezone'):
                # no per-admin time zone set in `login_auth()`
                timezone = settings.LOCAL_TIMEZONE
                session['timezone'] = timezone

        if qr_user_auth[0]:
            logger.info("Admin login success: username={}, client_address={}".format(username, web.ctx.ip))
            log_activity(msg="Admin login success", admin=username, event='login')

            qr_user_profile = ldap_lib_user.get_profile(mail=username, attributes=_attrs, conn=conn)
            if qr_user_profile[0]:
                # Time zone
                if not session.get('timezone'):
                    # no per-user time zone set in `login_auth()`
                    timezone = settings.LOCAL_TIMEZONE

                    # Get per-domain time zone
                    qr = ldap_lib_general.get_domain_account_setting(domain=domain, conn=conn)
                    if qr[0]:
                        _das = qr[1]
                        tz_name = _das.get('timezone')
                        if tz_name in TIMEZONES:
                            timezone = TIMEZONES[tz_name]

                    session['timezone'] = timezone

        # Save selected language
        selected_language = str(form.get('lang', '')).strip()
        if selected_language != web.ctx.lang and \
           selected_language in iredutils.get_language_maps():
            session['lang'] = selected_language

        # Save 'logged' at the end, if above settings are failed, it won't
        # redirect to other page and loop forever.
        session["logged"] = True

        if settings.REDIRECT_TO_DOMAIN_LIST_AFTER_LOGIN:
            raise web.seeother('/domains')
        else:
            raise web.seeother('/dashboard?checknew')


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
            session['new_version'] = _info      # if _status is True
            session['new_version_check_error'] = _info  # if _status is False

        # Get numbers of domains, users, aliases.
        num_existing_domains = ldap_lib_admin.num_managed_domains()

        # Get numbers of existing messages and quota bytes.
        # Set None as default, so that it's easy to detect them in Jinja2 template.
        total_messages = None
        total_bytes = None
        if settings.SHOW_USED_QUOTA:
            try:
                _qr = web.conn_iredadmin.query("""
                    SELECT
                    SUM(messages) AS total_messages, \
                    SUM(bytes) AS total_bytes \
                    FROM %s
                    """ % settings.SQL_TBL_USED_QUOTA)

                if _qr:
                    _row = _qr[0]
                    total_messages = _row.total_messages
                    total_bytes = _row.total_bytes
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
            num_existing_domains=num_existing_domains,
            total_messages=total_messages,
            total_bytes=total_bytes,
        )
