#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

#---------------------------------------------------------------------
# This file is part of iRedAdmin-OSE, which is official web-based admin
# panel (Open Source Edition) for iRedMail.
#
# iRedMail is an open source mail server solution for Red Hat(R)
# Enterprise Linux, CentOS, Debian and Ubuntu.
#
# iRedAdmin-OSE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# iRedAdmin-OSE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with iRedAdmin-OSE.  If not, see <http://www.gnu.org/licenses/>.
#---------------------------------------------------------------------

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
