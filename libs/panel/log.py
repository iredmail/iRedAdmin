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
        self.event = web.safestr(event)
        self.domain = web.safestr(domain)
        self.admin = web.safestr(admin)
        self.cur_page = int(cur_page)

        # Generate a dictionary, converted to an SQL WHERE clause.
        queryDict = {}
        if self.event in LOG_EVENTS and self.event != 'all':
            queryDict['event'] = self.event

        if iredutils.is_domain(self.domain):
            queryDict['domain'] = self.domain

        if session.get('domainGlobalAdmin') is not True:
            queryDict['admin'] = session.get('username')
        else:
            if iredutils.is_email(self.admin):
                queryDict['admin'] = self.admin

        # Get number of total records.
        if len(queryDict) == 0:
            qr = db.select('log', what='COUNT(timestamp) AS total',)
        else:
            qr = db.select('log', what='COUNT(timestamp) AS total', where=web.db.sqlwhere(queryDict),)

        self.total = qr[0].total or 0

        # Get records.
        if len(queryDict) == 0:
            # No addition filter.
            self.entries = db.select(
                'log',
                offset=(self.cur_page - 1) * settings.PAGE_SIZE_LIMIT,
                limit=settings.PAGE_SIZE_LIMIT,
                order='timestamp DESC',
            )
        else:
            # With filter.
            self.entries = db.select('log',
                    where=web.db.sqlwhere(queryDict),
                    offset=(self.cur_page - 1) * settings.PAGE_SIZE_LIMIT,
                    limit=settings.PAGE_SIZE_LIMIT,
                    order='timestamp DESC',
                    )

        return (self.total, list(self.entries))

    @decorators.require_global_admin
    @decorators.require_login
    def delete(self, data, deleteAll=False,):
        if deleteAll is True:
            try:
                db.query('''DELETE FROM log''')
                return (True,)
            except Exception, e:
                return (False, str(e))
        else:
            self.logIDs = data.get('id', [])
            if isinstance(self.logIDs, list) and len(self.logIDs) > 0:
                try:
                    db.query("""DELETE FROM log WHERE id in %s""" % web.db.sqlquote(self.logIDs))
                    return (True,)
                except Exception, e:
                    return (False, str(e))
            else:
                return (False, 'TYPE_ERROR')
