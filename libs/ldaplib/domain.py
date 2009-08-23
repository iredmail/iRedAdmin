#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import sys
import ldap
import web
from libs.ldaplib import core, attrs, iredldif, iredutils, deltree

session = web.config.get('_session')

class Domain(core.LDAPWrap):
    def __del__(self):
        pass

    def add(self, domainName, cn=None):
        # msg: {key: value}
        msg = {}
        domainName = iredutils.removeSpaceAndDot(web.safestr(domainName)).lower()
        if domainName == '' or domainName == 'None' or domainName is None:
            return False

        dn = iredutils.convDomainToDN(domainName)
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

    # List all domains.
    def list(self, attrs=attrs.DOMAIN_SEARCH_ATTRS):
        return self.get_all_domains(attrs)

    # Delete domain.
    def delete(self, domainName=[]):
        if domainName is None or len(domainName) == 0: return False
        
        msg = {}
        for domain in domainName:
            dn = iredutils.convDomainToDN(web.safestr(domain))

            try:
                deltree.DelTree( self.conn, dn, ldap.SCOPE_SUBTREE )
            except ldap.LDAPError, e:
                msg[domain] = str(e)

        if msg == {}: return True
        else: return False

    # Get domain attributes & values.
    def profile(self, domain):
        self.domain = web.safestr(domain)
        self.domainDN = iredutils.convDomainToDN(self.domain)

        # Access control.
        if self.check_domain_access(self.domainDN, session.get('username')):
            try:
                self.domain_detail = self.conn.search_s(
                        self.domainDN,
                        ldap.SCOPE_BASE,
                        '(objectClass=mailDomain)',
                        attrs.DOMAIN_ATTRS_ALL,
                        )
                if len(self.domain_detail) == 1:
                    return self.domain_detail
                else:
                    return False
            except:
                return False
        else:
            return False

    # Update domain profile.
    # data = web.input()
    def update(self, data):
        domain = web.safestr(data.get('domainName'))
        cn = data.get('cn', None)

        if cn is not None:
            mod_attrs = [ ( ldap.MOD_REPLACE, 'cn', cn.encode('utf-8') ) ]
        else:
            # Delete attribute.
            mod_attrs = [ ( ldap.MOD_DELETE, 'cn', None) ]

        if session.get('domainGlobalAdmin') == 'yes':
            # Convert to string, they don't contain non-ascii characters.
            domainBackupMX = web.safestr(data.get('domainBackupMX', 'no'))
            if domainBackupMX not in attrs.VALUES_DOMAIN_BACKUPMX:
                domainBackupMX = 'no'

            mod_attrs += [ (ldap.MOD_REPLACE, 'domainBackupMX', domainBackupMX) ]

            accountStatus = web.safestr(data.get('accountStatus', 'active'))
            if accountStatus not in attrs.VALUES_ACCOUNT_STATUS:
                accountStatus = 'active'

            mod_attrs += [ (ldap.MOD_REPLACE, 'accountStatus', accountStatus) ]
        else:
            pass

        try:
            dn = iredutils.convDomainToDN(domain)
            self.conn.modify_s(dn, mod_attrs)
            return True
        except Exception, e:
            return False
