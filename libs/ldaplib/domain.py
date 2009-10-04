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
import ldap
import web
from libs.ldaplib import core, attrs, iredldif, ldaputils, deltree

cfg = web.iredconfig
session = web.config.get('_session')
LDAPDecorators = core.LDAPDecorators()

class Domain(core.LDAPWrap):
    def __del__(self):
        pass

    @LDAPDecorators.check_global_admin
    def add(self, data):
        # msg: {key: value}
        msg = {}
        self.domain = web.safestr(data.get('domainName', None))
        if self.domain == 'None' or self.domain == '':
            return (False, 'msg=EMPTY_DOMAIN')
        
        self.domain = ldaputils.removeSpaceAndDot(self.domain.lower())
        self.dn = ldaputils.convDomainToDN(self.domain)

        self.cn = data.get('cn', None)
        ldif = iredldif.ldif_maildomain(domain=self.domain, cn=self.cn,)

        # Add domain dn.
        try:
            result = self.conn.add_s(self.dn, ldif)
        except ldap.ALREADY_EXISTS:
            msg[self.domain] = 'ALREADY_EXISTS'
        except ldap.LDAPError, e:
            msg[self.domain] = str(e)

        # Add domain groups.
        if len(attrs.DEFAULT_GROUPS) >= 1:
            for i in attrs.DEFAULT_GROUPS:
                try:
                    group_dn = 'ou=' + str(i) + ',' + str(self.dn)
                    group_ldif = iredldif.ldif_group(str(i))

                    self.conn.add_s(group_dn, group_ldif)
                except ldap.ALREADY_EXISTS:
                    pass
                except ldap.LDAPError, e:
                    msg[i] = str(e)
        else:
            pass

        if len(msg) == 0:
            return (True,)
        else:
            return (False, ldaputils.getExceptionDesc(msg))

    # List all domain admins.
    def admins(self, domain):
        domain = web.safestr(domain)
        dn = "domainName=" + domain + "," + self.basedn
        try:
            self.domainAdmins = self.conn.search_s(
                    dn,
                    ldap.SCOPE_BASE,
                    '(domainName=%s)' % domain,
                    ['domainAdmin'],
                    )
            return self.domainAdmins
        except Exception, e:
            return str(e)

    # List all domains under control.
    def list(self, attrs=attrs.DOMAIN_SEARCH_ATTRS):
        result = self.get_all_domains(attrs)
        if result[0] is True:
            allDomains = result[1]
            allDomains.sort()
            return (True, allDomains)
        else:
            return result

    # Get domain default user quota: domainDefaultUserQuota.
    def getDomainDefaultUserQuota(self, domain):
        self.domain = web.safestr(domain)
        self.dn = ldaputils.convDomainToDN(self.domain)

        try:
            result = self.conn.search_s(
                    self.dn,
                    ldap.SCOPE_BASE,
                    '(domainName=%s)' % self.domain,
                    ['domainDefaultUserQuota'],
                    )
            if result[0][1].has_key('domainDefaultUserQuota'):
                return result[0][1]['domainDefaultUserQuota'][0]
            else:
                return cfg.general.get('default_quota', '1024')
        except Exception, e:
            return cfg.general.get('default_quota', '1024')

    # Delete domain.
    @LDAPDecorators.check_global_admin
    def delete(self, domains=[]):
        if domains is None or len(domains) == 0: return False
        
        msg = {}
        for d in domains:
            dn = ldaputils.convDomainToDN(web.safestr(d))

            try:
                deltree.DelTree( self.conn, dn, ldap.SCOPE_SUBTREE )
            except ldap.LDAPError, e:
                msg[d] = str(e)

        if msg == {}: return (True,)
        else: return (False, ldaputils.getExceptionDesc(msg))

    @LDAPDecorators.check_global_admin
    def enableOrDisableAccount(self, domains, value, attr='accountStatus',):
        if domains is None or len(domains) == 0: return (False, 'msg=NO_DOMAIN_SELECTED')

        result = {}
        for domain in domains:
            self.domain = web.safestr(domain)
            self.dn = ldaputils.convDomainToDN(self.domain)

            try:
                self.updateAttrSingleValue(
                        dn=self.dn,
                        attr=web.safestr(attr),
                        value=web.safestr(value),
                        )
            except ldap.LDAPError, e:
                result[self.domain] = str(e)

        if result == {}:
            return (True,)
        else:
            return (False, ldaputils.getExceptionDesc(result))

    # Get domain attributes & values.
    @LDAPDecorators.check_domain_access
    def profile(self, domain):
        self.domain = web.safestr(domain)
        self.dn = ldaputils.convDomainToDN(self.domain)

        try:
            self.domain_profile = self.conn.search_s(
                    self.dn,
                    ldap.SCOPE_BASE,
                    '(&(objectClass=mailDomain)(domainName=%s))' % self.domain,
                    attrs.DOMAIN_ATTRS_ALL,
                    )
            if len(self.domain_profile) == 1:
                return (True, self.domain_profile)
            else:
                return (False, 'msg=NO_SUCH_DOMAIN')
        except ldap.NO_SUCH_OBJECT:
            return (False, 'msg=NO_SUCH_OBJECT')
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    # Update domain profile.
    # data = web.input()
    def update(self, profile_type, domain, data):
        self.profile_type = web.safestr(profile_type)
        self.domain = web.safestr(domain)

        mod_attrs = []
        if self.profile_type == 'general':
            cn = data.get('cn', None)
            mod_attrs += ldaputils.getSingleModAttr(attr='cn', value=cn, default=self.domain)

        if session.get('domainGlobalAdmin') == 'yes':
            # Get accountStatus.
            if data.has_key('accountStatus'): accountStatus = 'active'
            else: accountStatus = 'disabled'

            mod_attrs += [ (ldap.MOD_REPLACE, 'accountStatus', accountStatus) ]
        else:
            pass

        try:
            dn = ldaputils.convDomainToDN(self.domain)
            self.conn.modify_s(dn, mod_attrs)
            return (True,)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))
