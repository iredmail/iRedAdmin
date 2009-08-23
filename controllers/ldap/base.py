#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import sys
import web

session = web.config.get('_session')

class redirect:
    '''Make url ending with or without '/' going to the same class.
    '''
    def GET(self, path):
        web.redirect('/' + str(path))

#
# Decorators
#
def protected(func):
    def proxyfunc(self, *args, **kw):
        if session.get('username') != None and session.get('logged') == True:
            return func(self, *args, **kw)
        else:
            session.kill()
            web.seeother('/login?msg=loginRequired')
    return proxyfunc

def check_global_admin(func):
    def proxyfunc(self, *args, **kw):
        if session.get('domainGlobalAdmin') == 'yes':
            return func(self, *args, **kw)
        else:
            web.seeother('/domains?msg=PERMISSION_DENIED')
    return proxyfunc
