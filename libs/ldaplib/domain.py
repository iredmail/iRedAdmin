#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

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
    def add(self, domainName, cn=None):
        # msg: {key: value}
        msg = {}
        domainName = ldaputils.removeSpaceAndDot(web.safestr(domainName)).lower()
        if domainName == '' or domainName == 'None' or domainName is None:
            return False

        dn = ldaputils.convDomainToDN(domainName)
        ldif = iredldif.ldif_maildomain(domainName, cn)

        # Add domain dn.
        try:
            result = self.conn.add_s(dn, ldif)
        except ldap.ALREADY_EXISTS:
            msg[domainName] = 'ALREADY_EXISTS'
        except ldap.LDAPError, e:
            msg[domainName] = str(e)

        # Add domain groups.
        if len(attrs.DEFAULT_GROUPS) >= 1:
            for i in attrs.DEFAULT_GROUPS:
                try:
                    group_dn = 'ou=' + str(i) + ',' + str(dn)
                    group_ldif = iredldif.ldif_group(str(i))

                    self.conn.add_s(group_dn, group_ldif)
                except ldap.ALREADY_EXISTS:
                    pass
                except ldap.LDAPError, e:
                    msg[i] = str(e)
        else:
            pass

        if len(msg) == 0:
            return True
        else:
            return msg

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
        allDomains = self.get_all_domains(attrs)
        allDomains.sort()
        return allDomains

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
    def delete(self, domain=[]):
        if domain is None or len(domain) == 0: return False
        
        msg = {}
        for d in domain:
            dn = ldaputils.convDomainToDN(web.safestr(d))

            try:
                deltree.DelTree( self.conn, dn, ldap.SCOPE_SUBTREE )
            except ldap.LDAPError, e:
                msg[d] = str(e)

        if msg == {}: return True
        else: return False

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
                return (False, 'NO_SUCH_DOMAIN')
        except ldap.NO_SUCH_OBJECT:
            return (False, 'NO_SUCH_OBJECT')
        except Exception, e:
            return (False, str(e))

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
            accountStatus = web.safestr(data.get('accountStatus', 'active'))
            if accountStatus not in attrs.VALUES_ACCOUNT_STATUS:
                accountStatus = 'active'

            mod_attrs += [ (ldap.MOD_REPLACE, 'accountStatus', accountStatus) ]
        else:
            pass

        try:
            dn = ldaputils.convDomainToDN(self.domain)
            self.conn.modify_s(dn, mod_attrs)
            return (True, 'SUCCESS')
        except Exception, e:
            return (False, str(e))
