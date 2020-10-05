# Author: Zhang Huangbin <zhb@iredmail.org>

import web

import settings
from libs import iredutils
from libs.panel import LOG_EVENTS

if settings.backend == 'ldap':
    from libs.ldaplib.general import is_domain_admin
else:
    from libs.sqllib.general import is_domain_admin

session = web.config.get('_session')


def list_logs(event='all', domain='all', admin='all', cur_page=1):
    event = web.safestr(event)
    domain = web.safestr(domain)
    admin = web.safestr(admin)
    cur_page = int(cur_page)

    sql_vars = {}
    sql_wheres = []
    sql_where = ''

    if event in LOG_EVENTS and event != 'all':
        sql_vars['event'] = event
        sql_wheres += ["event=$event"]

    if iredutils.is_domain(domain):
        if session.get('is_global_admin') or is_domain_admin(domain=domain, admin=session['username'], conn=None):
            sql_vars['domain'] = domain
            sql_wheres += ["domain=$domain"]

    if not session.get('is_global_admin'):
        sql_vars['admin'] = session.get('username')
        sql_wheres += ["admin=$admin"]
    else:
        if iredutils.is_email(admin):
            sql_vars['admin'] = admin
            sql_wheres += ["admin=$admin"]

    # Get number of total records.
    if sql_wheres:
        sql_where = ' AND '.join(sql_wheres)

        qr = web.conn_iredadmin.select(
            'log',
            vars=sql_vars,
            what='COUNT(id) AS total',
            where=sql_where,
        )
    else:
        qr = web.conn_iredadmin.select('log', what='COUNT(id) AS total')

    total = qr[0].total or 0

    # Get records.
    if sql_wheres:
        qr = web.conn_iredadmin.select(
            'log',
            vars=sql_vars,
            where=sql_where,
            offset=(cur_page - 1) * settings.PAGE_SIZE_LIMIT,
            limit=settings.PAGE_SIZE_LIMIT,
            order='timestamp DESC',
        )
    else:
        # No addition filter.
        qr = web.conn_iredadmin.select(
            'log',
            offset=(cur_page - 1) * settings.PAGE_SIZE_LIMIT,
            limit=settings.PAGE_SIZE_LIMIT,
            order='timestamp DESC',
        )

    return (total, list(qr))


def delete_logs(form, delete_all=False):
    if delete_all:
        try:
            web.conn_iredadmin.delete('log')
            return (True, )
        except Exception as e:
            return (False, repr(e))
    else:
        ids = form.get('id', [])

        if ids:
            try:
                web.conn_iredadmin.delete('log', where="id IN %s" % web.db.sqlquote(ids))
                return (True, )
            except Exception as e:
                return (False, repr(e))

    return (True, )
