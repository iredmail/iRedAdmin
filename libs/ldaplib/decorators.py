# Author: Zhang Huangbin <zhb@iredmail.org>

import ldap
import web
from controllers import decorators as base_decorators
from libs import iredutils
from libs.ldaplib import core, ldaputils, attrs

session = web.config.get('_session')

require_login = base_decorators.require_login
require_global_admin = base_decorators.require_global_admin
csrf_protected = base_decorators.csrf_protected

class Validator(core.LDAPWrap):
    def __del__(self):
        try:
            self.conn.unbind()
        except Exception:
            pass

    def is_domainAdmin(self, domain, admin=session.get('username'),):
        dn = ldaputils.convert_keyword_to_dn(domain, accountType='domain')
        try:
            result = self.conn.search_s(
                dn,
                ldap.SCOPE_BASE,
                "(&(%s=%s)(domainAdmin=%s))" % (attrs.RDN_DOMAIN, domain, admin),
                ['dn', 'domainAdmin'],
            )
            if len(result) >= 1:
                return True
            else:
                return False
        except Exception:
            return False


def require_domain_access(func):
    def proxyfunc(*args, **kw):
        # Check domain global admin.
        if session.get('domainGlobalAdmin') is True:
            return func(*args, **kw)
        else:
            if 'mail' in kw.keys() and iredutils.is_email(kw.get('mail')):
                domain = web.safestr(kw['mail']).split('@')[-1]
            elif 'domain' in kw.keys() and iredutils.is_domain(kw.get('domain')):
                domain = web.safestr(kw['domain'])
            else:
                return (False, 'PERMISSION_DENIED')

            # Check whether is domain admin.
            validator = Validator()
            if validator.is_domainAdmin(domain=domain, admin=session.get('username'),):
                return func(*args, **kw)
            else:
                return (False, 'PERMISSION_DENIED')
    return proxyfunc
