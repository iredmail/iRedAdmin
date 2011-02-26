# Author: Zhang Huangbin <zhb@iredmail.org>

import sys
import ldap
import web
from libs import iredutils
from libs.ldaplib import core, ldaputils, attrs

session = web.config.get('_session')

class Validator(core.LDAPWrap):
    def __del__(self):
        try:
            self.conn.unbind()
        except Exception, e:
            pass

    def isDomainAdmin(self, domain, admin=session.get('username'),):
        dn = ldaputils.convKeywordToDN(domain, accountType='domain')
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
        except Exception, e:
            return False

    
def require_global_admin(func):
    def proxyfunc(*args, **kw):
        if session.get('domainGlobalAdmin') is True:
            return func(*args, **kw)
        else:
            return (False, 'PERMISSION_DENIED')
    return proxyfunc

def require_domain_access(func):
    def proxyfunc(*args, **kw):
        # Check domain global admin.
        if session.get('domainGlobalAdmin') is True:
            return func(*args, **kw)
        else:
            if 'mail' in kw.keys() and iredutils.isEmail(kw.get('mail')):
                domain = web.safestr(kw['mail']).split('@')[-1]
            elif 'domain' in kw.keys() and iredutils.isDomain(kw.get('domain')):
                domain = web.safestr(kw['domain'])
            else:
                return (False, 'PERMISSION_DENIED')

            # Check whether is domain admin.
            validator = Validator()
            if validator.isDomainAdmin(domain=domain, admin=session.get('username'),):
                return func(*args, **kw)
            else:
                return (False, 'PERMISSION_DENIED')
    return proxyfunc
