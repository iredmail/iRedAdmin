# encoding: utf-8

# Author: Zhang Huangbin <zhb@iredmail.org>

import web
from libs import iredutils
from libs.mysql import core

session = web.config.get('_session')

def require_login(func):
    def proxyfunc(self, *args, **kw):
        if session.get('logged') is True:
            return func(self, *args, **kw)
        else:
            session.kill()
            return web.seeother('/login?msg=loginRequired')
    return proxyfunc

def require_global_admin(func):
    def proxyfunc(*args, **kw):
        if session.get('domainGlobalAdmin') is True:
            return func(*args, **kw)
        else:
            return web.seeother('/domains?msg=PERMISSION_DENIED')
    return proxyfunc

def require_domain_access(func):
    def proxyfunc(*args, **kw):
        # Check domain global admin.
        if session.get('domainGlobalAdmin') is True:
            return func(*args, **kw)
        else:
            if 'domain' in kw.keys() and iredutils.isDomain(kw.get('domain')):
                domain = web.safestr(kw['domain'])
            elif 'mail' in kw.keys() and iredutils.isEmail(kw.get('mail')):
                domain = web.safestr(kw['mail']).split('@')[-1]
            elif 'admin' in kw.keys() and iredutils.isEmail(kw.get('admin')):
                domain = web.safestr(kw['admin']).split('@')[-1]
            else:
                return (False, 'PERMISSION_DENIED')

            # Check whether is domain admin.
            validator = core.MySQLWrap()
            if validator.isDomainAdmin(domain=domain, admin=session.get('username'),):
                return func(*args, **kw)
            else:
                return (False, 'PERMISSION_DENIED')
    return proxyfunc
