# Author: Zhang Huangbin <zhb@iredmail.org>

import web
from libs import iredutils

session = web.config.get("_session")


def require_login(func):
    def proxyfunc(*args, **kw):
        if session.get("logged") is True:
            return func(*args, **kw)
        else:
            session.kill()
            raise web.seeother("/login?msg=LOGIN_REQUIRED")

    return proxyfunc


def require_global_admin(func):
    def proxyfunc(*args, **kw):
        if session.get("is_global_admin"):
            return func(*args, **kw)
        else:
            if session.get("logged"):
                raise web.seeother("/domains?msg=PERMISSION_DENIED")
            else:
                raise web.seeother("/login?msg=LOGIN_REQUIRED")

    return proxyfunc


def csrf_protected(f):
    def decorated(*args, **kw):
        form = web.input()

        if "csrf_token" not in form:
            return web.render("error_csrf.html")

        if not session.get("csrf_token"):
            session["csrf_token"] = iredutils.generate_random_strings(32)

        if form["csrf_token"] != session["csrf_token"]:
            return web.render("error_csrf.html")

        return f(*args, **kw)

    return decorated
