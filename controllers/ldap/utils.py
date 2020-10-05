import web
from controllers import decorators
from libs.ldaplib import domain as ldap_lib_domain


# Get all domains, select the first one.
class CreateDispatcher:
    @decorators.require_global_admin
    def GET(self, account_type):
        qr = ldap_lib_domain.list_accounts(attributes=['domainName'], names_only=True, conn=None)
        if qr[0]:
            all_domains = qr[1]

            if all_domains:
                # Create new account under first domain, so that we
                # can get per-domain account settings, such as number of
                # account limit, password length control, etc.
                raise web.seeother('/create/{}/{}'.format(account_type, all_domains[0]))
            else:
                raise web.seeother('/domains?msg=NO_DOMAIN_AVAILABLE')
        else:
            raise web.seeother('/domains?msg=' + web.urlquote(qr[1]))
