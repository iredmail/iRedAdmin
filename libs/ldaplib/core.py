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

import os, sys, time
import web
import ldap, ldap.filter
from libs import iredutils
from libs.ldaplib import attrs, ldaputils

cfg = web.iredconfig
session = web.config.get('_session')

class LDAPWrap:
    def __init__(self, app=web.app, session=session, **settings):
        # Get LDAP settings.
        self.basedn = cfg.ldap.get('basedn')
        self.domainadmin_dn = cfg.ldap.get('domainadmin_dn')

        # Initialize LDAP connection.
        try:
            self.conn = ldap.initialize(
                    uri=cfg.ldap.get('uri', 'ldap://127.0.0.1:389'),
                    trace_level=int(cfg.ldap.get('trace_level', 0)),
                    )

            #self.conn.protocol_version = ldap.VERSION3
            # Set LDAP protocol version.
            pro_version = int(cfg.ldap.get('protocol_version', 0))
            if pro_version:
                self.conn.set_option(ldap.OPT_PROTOCOL_VERSION, pro_version)
            else:
                self.conn.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

        use_tls = eval(cfg.ldap.get('use_tls', '0'))
        if use_tls:
            try:
                self.conn.start_tls_s()
            except ldap.LDAPError, e:
                return (False, ldaputils.getExceptionDesc(e))

        # synchronous bind.
        self.conn.bind_s(cfg.ldap.get('bind_dn'), cfg.ldap.get('bind_pw'))

    def __del__(self):
        self.conn.unbind()

    def change_passwd(self, dn, cur_passwd, newpw):
        dn = ldap.filter.escape_filter_chars(dn)
        try:
            # Reference: RFC3062 - LDAP Password Modify Extended Operation
            self.conn.passwd_s(dn, cur_passwd, newpw)
            return (True,)
        except ldap.UNWILLING_TO_PERFORM:
            return (False, 'msg=INCORRECT_OLDPW')
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    def updateAttrSingleValue(self, dn, attr, value):
        self.mod_attrs = [
                ( ldap.MOD_REPLACE, web.safestr(attr), web.safestr(value) )
                ]
        try:
            result = self.conn.modify_s(web.safestr(dn), self.mod_attrs)
            return (True,)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    # List all domains.
    def get_all_domains(self, attrs=attrs.DOMAIN_SEARCH_ATTRS):
        admin = session.get('username', None)
        if admin is None: return False

        # Check whether admin is a site wide admin.
        if session.get('domainGlobalAdmin') == 'yes':
            filter = '(objectClass=mailDomain)'
        else:
            filter = '(&(objectClass=mailDomain)(domainAdmin=%s))' % (admin)

        # List all domains under control.
        try:
            self.domains = self.conn.search_s(
                    self.basedn,
                    ldap.SCOPE_ONELEVEL,
                    filter,
                    attrs,
                    )
            return (True, self.domains)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

class LDAPDecorators(LDAPWrap):
    def __del__(self):
        pass

    def check_global_admin(self, func):
        def proxyfunc(self, *args, **kw):
            if session.get('domainGlobalAdmin') == 'yes':
                return func(self, *args, **kw)
            else:
                return False
        return proxyfunc

    def check_domain_access(self, func):
        def proxyfunc(self, *args, **kw):
            if kw.has_key('mail'):
                self.domain = web.safestr(kw['mail']).split('@', 1)[1]
            elif kw.has_key('domain'):
                self.domain = web.safestr(kw['domain'])

            if self.domain is None or self.domain == '': return False

            self.dn = ldaputils.convDomainToDN(self.domain)
            self.admin = session.get('username')

            # Check domain global admin.
            if session.get('domainGlobalAdmin') == 'yes':
                return func(self, *args, **kw)
            else:
                # Check whether is domain admin.
                result = self.conn.search_s(
                        self.dn,
                        ldap.SCOPE_BASE,
                        "(&(domainName=%s)(domainAdmin=%s))" % (self.domain, self.admin),
                        ['dn', 'domainAdmin'],
                        )
                if len(result) == 0:
                    web.seeother('/users' + '?msg=PERMISSION_DENIED&domain=' + self.domain)
                else:
                    return func(self, *args, **kw)
        return proxyfunc
