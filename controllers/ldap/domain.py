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
from web import render
from web import iredconfig as cfg
from controllers import base
from controllers.ldap.basic import dbinit
from libs.ldaplib import core, admin, domain, attrs

session = web.config.get('_session')

adminLib = admin.Admin()
domainLib = domain.Domain()

#
# Domain related.
#
class list(dbinit):
    '''List all virtual mail domains.'''
    @base.require_login
    def GET(self):
        i = web.input()
        result = domainLib.list()
        if result[0] is True:
            allDomains = result[1]
        else:
            return result
        return render.domains(allDomains=allDomains, msg=i.get('msg', None))

    @base.require_global_admin
    @base.require_login
    def POST(self):
        i = web.input(domainName=[])
        domainName = i.get('domainName', None)
        if i.has_key('delete'):
            result = domainLib.delete(domains=domainName)
            msg = 'DELETED_SUCCESS'
        elif i.has_key('disable'):
            result = domainLib.enableOrDisableAccount(domains=domainName, value='disabled',)
            msg = 'DISABLED_SUCCESS'
        elif i.has_key('enable'):
            result = domainLib.enableOrDisableAccount(domains=domainName, value='active',)
            msg = 'ENABLED_SUCCESS'
        else:
            msg = i.get('msg', None)

        if result[0] is True:
            web.seeother('/domains?msg=%s' % msg)
        else:
            web.seeother('/domains?' + result[1])

class profile(dbinit):
    @base.require_login
    def GET(self, profile_type, domain):
        i = web.input()
        self.domain = web.safestr(domain.split('/', 1)[0])
        self.profile_type = web.safestr(profile_type)
        if self.domain == '' or self.domain is None:
            web.seeother('/domains?msg=EMPTY_DOMAIN')

        if self.profile_type not in attrs.DOMAIN_PROFILE_TYPE:
            web.seeother('/domains?msg=INCORRECT_PROFILE_TYPE')

        result = domainLib.profile(domain=self.domain)

        if result[0] is True:
            r = domainLib.list(attrs=['domainName'])
            if r[0] is True:
                allDomains = r[1]
            else:
                return r
            allAdmins = adminLib.list()
            domainAdmins = domainLib.admins(self.domain)

            return render.domain_profile(
                    cur_domain=self.domain,
                    allDomains=allDomains,
                    profile=result[1],
                    profile_type=self.profile_type,
                    admins=allAdmins,
                    # We need only mail address of domain admins.
                    domainAdmins=domainAdmins[0][1].get('domainAdmin', []),
                    msg=i.get('msg', None),
                    )
        else:
            web.seeother('/domains?' + result[1])

    @base.require_login
    def POST(self, profile_type, domain):
        self.profile_type = web.safestr(profile_type)
        self.domain = web.safestr(domain)

        i = web.input(enabledService=[],)

        result = domainLib.update(
                profile_type=self.profile_type,
                domain=self.domain,
                data=i,
                )
        if result[0] is True:
            web.seeother('/profile/domain/%s/%s?msg=PROFILE_UPDATED_SUCCESS' % (self.profile_type, self.domain) )
        elif result[0] is False:
            web.seeother('/profile/domain/%s/%s?' % (self.profile_type, self.domain) + result[1])

class create(dbinit):
    @base.require_global_admin
    @base.require_login
    def GET(self):
        i = web.input()
        return render.domain_create(msg=i.get('msg'))

    @base.require_global_admin
    @base.require_login
    def POST(self):
        i = web.input()
        result = domainLib.add(data=i)
        if result[0] is True:
            web.seeother('/domains?msg=CREATED_SUCCESS')
        else:
            web.seeother('/create/domain?' + result[1])
