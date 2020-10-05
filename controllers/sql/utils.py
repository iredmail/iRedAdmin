import web
from controllers import decorators
from libs.sqllib import SQLWrap
from libs.sqllib import domain as sql_lib_domain


# Get all domains, select the first one.
class CreateDispatcher:
    @decorators.require_global_admin
    def GET(self, account_type):
        _wrap = SQLWrap()
        conn = _wrap.conn

        qr = sql_lib_domain.get_all_domains(conn=conn, name_only=True)

        if qr[0] is True:
            all_domains = qr[1]

            # Go to first available domain.
            if all_domains:
                raise web.seeother('/create/{}/{}'.format(account_type, all_domains[0]))
            else:
                raise web.seeother('/domains?msg=NO_DOMAIN_AVAILABLE')
        else:
            raise web.seeother('/domains?msg=' + web.urlquote(qr[1]))
