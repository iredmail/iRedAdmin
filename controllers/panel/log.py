# Author: Zhang Huangbin <zhb@iredmail.org>

import web
from controllers import decorators
from libs.panel import LOG_EVENTS, log as loglib

session = web.config.get('_session')


class Log:
    @decorators.require_login
    def GET(self):
        i = web.input(_unicode=False,)

        # Get queries.
        self.event = web.safestr(i.get('event', 'all'))
        self.domain = web.safestr(i.get('domain', 'all'))
        self.admin = web.safestr(i.get('admin', 'all'))
        self.cur_page = web.safestr(i.get('page', '1'))

        if not self.cur_page.isdigit() or self.cur_page == '0':
            self.cur_page = 1
        else:
            self.cur_page = int(self.cur_page)

        logLib = loglib.Log()
        total, entries = logLib.listLogs(
                event=self.event,
                domain=self.domain,
                admin=self.admin,
                cur_page=self.cur_page,
                )

        return web.render(
            'panel/log.html',
            event=self.event,
            domain=self.domain,
            admin=self.admin,
            log_events=LOG_EVENTS,
            cur_page=self.cur_page,
            total=total,
            entries=entries,
            msg=i.get('msg'),
        )

    @decorators.require_global_admin
    @decorators.csrf_protected
    @decorators.require_login
    def POST(self):
        i = web.input(_unicode=False, id=[],)
        action = web.safestr(i.get('action', 'delete'))

        deleteAll = False
        if action == 'deleteAll':
            deleteAll = True

        logLib = loglib.Log()
        result = logLib.delete(data=i, deleteAll=deleteAll,)

        if result[0] is True:
            raise web.seeother('/system/log?msg=DELETED')
        else:
            raise web.seeother('/system/log?msg=%s' % web.urlquote(result[1]))
