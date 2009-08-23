#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import sys
import web
from web import render
from web import iredconfig as cfg
from controllers.ldap import base
from controllers.ldap.core import dbinit
from libs.ldaplib import core, admin, domain, iredutils

session = web.config.get('_session')

adminLib = admin.Admin()
domainLib = domain.Domain()

#
# Domain related.
#
class list(dbinit):
    '''List all virtual mail domains.'''
    @base.protected
    def GET(self):
        self.domains = domainLib.list()
        return render.domains(domains=self.domains)

    @base.check_global_admin
    @base.protected
    def POST(self):
        i = web.input(domainName=[])
        domainName = i.get('domainName', None)
        result = domainLib.delete(domainName)
        web.seeother('/domains')

class profile(dbinit):
    @base.protected
    def GET(self, domain):
        domain = web.safestr(domain.split('/', 1)[0])
        if domain is '' or domain is None:
            web.seeother('/domains?msg=NO_SUCH_DOMAIN')

        domain = web.safestr(domain)
        profile = domainLib.profile(domain)
        allAdmins = adminLib.list()
        domainAdmins = domainLib.admins(domain)
        
        if profile:
            return render.domain_profile(
                    domain=domain,
                    profile=profile,
                    admins=allAdmins,
                    # We need only mail address of domain admins.
                    domainAdmins=domainAdmins[0][1].get('domainAdmin', []),
                    )
        else:
            return render.domains(msg='NO_SUCH_DOMAIN')

    @base.protected
    def POST(self, domain):
        i = web.input(enabledService=[])
        self.result = domainLib.update(data=i)
        if self.result:
            web.seeother('/profile/domain/' + web.safestr(domain) + '?msg=SUCCESS')
        else:
            web.seeother('/profile/domain/' + web.safestr(domain))

class create(dbinit):
    @base.check_global_admin
    @base.protected
    def GET(self):
        return render.domain_create()

    @base.check_global_admin
    @base.protected
    def POST(self):
        i = web.input()
        domainName = i.get('domainName', None)
        cn = i.get('cn', None)
        result = domainLib.add(domainName=domainName, cn=cn)
        if result is True:
            web.seeother('/domains')
        else:
            return render.domain_create(msg=result)
