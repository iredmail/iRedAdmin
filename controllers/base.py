# Author: Zhang Huangbin <zhb@iredmail.org>

import web

session = web.config.get('_session')

class redirect:
    '''Make url ending with or without '/' going to the same class.
    '''
    def GET(self, path):
        return web.seeother('/' + str(path))

class img:
    def GET(self, encoded_img):
        web.header('Content-Type', 'image/jpeg')
        return encoded_img.decode('base64')

#
# Decorators
#
def require_login(func):
    def proxyfunc(self, *args, **kw):
        if session.get('logged') is True:
            return func(self, *args, **kw)
        else:
            session.kill()
            return web.seeother('/login?msg=loginRequired')
    return proxyfunc

def require_global_admin(func):
    def proxyfunc(self, *args, **kw):
        if session.get('domainGlobalAdmin') is True:
            return func(self, *args, **kw)
        else:
            return web.seeother('/domains?msg=PERMISSION_DENIED')
    return proxyfunc
