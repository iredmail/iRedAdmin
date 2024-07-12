# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings
from controllers import decorators
from libs import iredutils
from libs.panel import LOG_EVENTS, log as loglib

session = web.config.get('_session')

if settings.backend == 'ldap':
    from libs.ldaplib.core import LDAPWrap
    from libs.ldaplib import admin as ldap_lib_admin
elif settings.backend in ['mysql', 'pgsql']:
    from libs.sqllib import SQLWrap, admin as sql_lib_admin


class Log:
    @decorators.require_global_admin
    def GET(self):
        form = web.input(_unicode=False)

        # Get queries.
        form_event = web.safestr(form.get('event', 'all'))
        form_domain = web.safestr(form.get('domain', 'all'))
        form_admin = web.safestr(form.get('admin', 'all'))
        form_cur_page = web.safestr(form.get('page', '1'))

        # Verify input data.
        if form_event not in LOG_EVENTS:
            form_event = "all"

        if not iredutils.is_domain(form_domain):
            form_domain = ""

        if not iredutils.is_email(form_admin):
            form_admin = ""

        if not form_cur_page.isdigit() or form_cur_page == '0':
            form_cur_page = 1
        else:
            form_cur_page = int(form_cur_page)

        total, entries = loglib.list_logs(event=form_event,
                                          domain=form_domain,
                                          admin=form_admin,
                                          cur_page=form_cur_page)

        # Pre-defined
        all_domains = []
        all_admins = []

        if settings.backend == 'ldap':
            _wrap = LDAPWrap()
            conn = _wrap.conn

            # Get all managed domains under control.
            qr = ldap_lib_admin.get_managed_domains(admin=session.get('username'), conn=conn)
            if qr[0] is True:
                all_domains = qr[1]

            # Get all admins.
            if session.get('is_global_admin') is True:
                result = ldap_lib_admin.list_accounts(attributes=['mail'], conn=conn)
                if result[0] is not False:
                    all_admins = [v[1]['mail'][0] for v in result[1]]
            else:
                all_admins = [form_admin]

        elif settings.backend in ['mysql', 'pgsql']:
            # Get all managed domains under control.
            _wrap = SQLWrap()
            conn = _wrap.conn
            qr = sql_lib_admin.get_managed_domains(conn=conn,
                                                   admin=session.get('username'),
                                                   domain_name_only=True)
            if qr[0] is True:
                all_domains = qr[1]

            # Get all admins.
            if session.get('is_global_admin') is True:
                qr = sql_lib_admin.get_all_admins(columns=['username'], email_only=True, conn=conn)
                if qr[0]:
                    all_admins = qr[1]
            else:
                all_admins = [form_admin]

        return web.render('panel/log.html',
                          event=form_event,
                          domain=form_domain,
                          admin=form_admin,
                          log_events=LOG_EVENTS,
                          cur_page=form_cur_page,
                          total=total,
                          entries=entries,
                          all_domains=all_domains,
                          all_admins=all_admins,
                          msg=form.get('msg'))

    @decorators.require_global_admin
    @decorators.csrf_protected
    @decorators.require_global_admin
    def POST(self):
        form = web.input(_unicode=False, id=[])
        action = form.get('action', 'delete')

        delete_all = False
        if action == 'deleteAll':
            delete_all = True

        qr = loglib.delete_logs(form=form, delete_all=delete_all)
        if qr[0]:
            # Keep the log filter.
            form_domain = web.safestr(form.get('domain'))
            form_admin = web.safestr(form.get('admin'))
            form_event = web.safestr(form.get('event'))
            url = 'domain={}&admin={}&event={}'.format(form_domain, form_admin, form_event)

            raise web.seeother('/activities/admins?%s&msg=DELETED' % url)
        else:
            raise web.seeother('/activities/admins?msg=%s' % web.urlquote(qr[1]))
