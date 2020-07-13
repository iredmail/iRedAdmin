# Author: Zhang Huangbin <zhb@iredmail.org>

import web
from controllers import decorators
import settings
from libs import iredutils
from libs.panel import LOG_EVENTS

db = web.admindb
session = web.config.get('_session')


class Log:
    @decorators.require_login
    def listLogs(self, event='all', domain='all', admin='all', cur_page=1):
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
            sql_vars['domain'] = domain
            sql_wheres += ["domain=$domain"]

        if session.get('domainGlobalAdmin') is not True:
            sql_vars['admin'] = session.get('username')
            sql_wheres += ["admin=$admin"]
        else:
            if iredutils.is_email(admin):
                sql_vars['admin'] = admin
                sql_wheres += ["admin=$admin"]

        # Get number of total records.
        if sql_wheres:
            sql_where = ' AND '.join(sql_wheres)

            qr = db.select('log',
                           vars=sql_vars,
                           what='COUNT(timestamp) AS total',
                           where=sql_where)
        else:
            qr = db.select('log', what='COUNT(timestamp) AS total')

        total = qr[0].total or 0

        # Get records.
        if sql_wheres:
            # With filter.
            qr = db.select('log',
                           vars=sql_vars,
                           where=sql_where,
                           offset=(cur_page - 1) * settings.PAGE_SIZE_LIMIT,
                           limit=settings.PAGE_SIZE_LIMIT,
                           order='timestamp DESC')
        else:
            # No addition filter.
            qr = db.select('log',
                           offset=(cur_page - 1) * settings.PAGE_SIZE_LIMIT,
                           limit=settings.PAGE_SIZE_LIMIT,
                           order='timestamp DESC')

        return (total, list(qr))

    @decorators.require_global_admin
    @decorators.require_login
    def delete(self, data, deleteAll=False,):
        if deleteAll is True:
            try:
                db.query('''DELETE FROM log''')
                return (True,)
            except Exception as e:
                return (False, str(e))
        else:
            self.logIDs = data.get('id', [])
            if isinstance(self.logIDs, list) and len(self.logIDs) > 0:
                try:
                    db.query("""DELETE FROM log WHERE id in %s""" % web.db.sqlquote(self.logIDs))
                    return (True,)
                except Exception as e:
                    return (False, str(e))
            else:
                return (False, 'TYPE_ERROR')
