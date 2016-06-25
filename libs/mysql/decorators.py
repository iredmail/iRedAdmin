# encoding: utf-8

# Author: Zhang Huangbin <zhb@iredmail.org>

import web
from controllers import decorators as base_decorators
from libs import iredutils
from libs.mysql import core

session = web.config.get('_session')

require_login = base_decorators.require_login
require_global_admin = base_decorators.require_global_admin
csrf_protected = base_decorators.csrf_protected


def require_domain_access(func):
    def proxyfunc(*args, **kw):
        # Check domain global admin.
        if session.get('domainGlobalAdmin') is True:
            return func(*args, **kw)
        else:
            if 'domain' in kw.keys() and iredutils.is_domain(kw.get('domain')):
                domain = web.safestr(kw['domain'])
            elif 'mail' in kw.keys() and iredutils.is_email(kw.get('mail')):
                domain = web.safestr(kw['mail']).split('@')[-1]
            elif 'admin' in kw.keys() and iredutils.is_email(kw.get('admin')):
                domain = web.safestr(kw['admin']).split('@')[-1]
            else:
                return (False, 'PERMISSION_DENIED')

            # Check whether is domain admin.
            validator = core.MySQLWrap()
            if validator.is_domainAdmin(domain=domain, admin=session.get('username'),):
                return func(*args, **kw)
            else:
                return (False, 'PERMISSION_DENIED')
    return proxyfunc
