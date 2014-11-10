# Author: Zhang Huangbin <zhb@iredmail.org>

import web

session = web.config.get('_session')


def require_login(func):
    def proxyfunc(self, *args, **kw):
        if session.get('logged') is True:
            return func(self, *args, **kw)
        else:
            session.kill()
            raise web.seeother('/login?msg=loginRequired')
    return proxyfunc


def require_global_admin(func):
    def proxyfunc(self, *args, **kw):
        if session.get('domainGlobalAdmin') is True:
            return func(self, *args, **kw)
        else:
            if session.get('logged'):
                raise web.seeother('/domains?msg=PERMISSION_DENIED')
            else:
                raise web.seeother('/login?msg=PERMISSION_DENIED')
    return proxyfunc


def csrf_protected(f):
    def decorated(*args, **kw):
        inp = web.input()
        if not ('csrf_token' in inp and \
                inp.csrf_token == session.pop('csrf_token', None)):
            return web.render('error_csrf.html')
        return f(*args, **kw)
    return decorated

