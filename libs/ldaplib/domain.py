# Author: Zhang Huangbin <zhb@iredmail.org>

import ldap
import types
import web
from libs import iredutils, models
from libs.ldaplib import core, attrs, iredldif, ldaputils, deltree, connUtils, decorators

cfg = web.iredconfig
session = web.config.get('_session')


class Domain(core.LDAPWrap):
    def __del__(self):
        try:
            self.conn.unbind()
        except:
            pass

    @decorators.require_global_admin
    def add(self, data):
        # msg: {key: value}
        msg = {}
        self.domain = web.safestr(data.get('domainName', '')).strip().lower()

        # Check domain name.
        if not iredutils.isDomain(self.domain):
            return (False, 'INVALID_DOMAIN_NAME')

        # Check whether domain name already exist (domainName, domainAliasName).
        connutils = connUtils.Utils()
        if connutils.isDomainExists(self.domain):
            return (False, 'ALREADY_EXISTS')

        self.dn = ldaputils.convKeywordToDN(self.domain, accountType='domain')

        self.cn = data.get('cn', None)
        ldif = iredldif.ldif_maildomain(domain=self.domain, cn=self.cn,)

        # Add domain dn.
        try:
            result = self.conn.add_s(self.dn, ldif)
            web.logger(msg="Create domain: %s." % (self.domain), domain=self.domain, event='create',)
        except ldap.ALREADY_EXISTS:
            msg[self.domain] = 'ALREADY_EXISTS'
        except ldap.LDAPError, e:
            msg[self.domain] = str(e)

        # Add default groups under domain.
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
    def getDomainAdmins(self, domain):
        domain = web.safestr(domain)
        dn = ldaputils.convKeywordToDN(domain, accountType='domain')
        try:
            self.domainAdmins = self.conn.search_s(
                    dn,
                    ldap.SCOPE_BASE,
                    '(&(objectClass=mailDomain)(domainName=%s))' % domain,
                    ['domainAdmin'],
                    )
            return self.domainAdmins
        except Exception, e:
            return str(e)

    # List all domains under control.
    def listAccounts(self, attrs=attrs.DOMAIN_SEARCH_ATTRS):
        result = self.getAllDomains(attrs=attrs)
        if result[0] is True:
            allDomains = result[1]
            allDomains.sort()
            return (True, allDomains)
        else:
            return result

    # Get domain default user quota: domainDefaultUserQuota.
    # - domainAccountSetting must be a dict.
    def getDomainDefaultUserQuota(self, domain, domainAccountSetting=None,):
        # Return 0 as unlimited.
        self.domain = web.safestr(domain)
        self.dn = ldaputils.convKeywordToDN(self.domain, accountType='domain')

        if domainAccountSetting is not None:
            if 'defaultQuota' in domainAccountSetting.keys():
                return int(domainAccountSetting['defaultQuota'])
            else:
                return 0
        else:
            try:
                result = self.conn.search_s(
                        self.dn,
                        ldap.SCOPE_BASE,
                        '(domainName=%s)' % self.domain,
                        ['domainName', 'accountSetting'],
                        )

                settings = ldaputils.getAccountSettingFromLdapQueryResult(result, key='domainName',)

                if 'defaultQuota' in settings[self.domain].keys():
                    return int(settings[self.domain]['defaultQuota'])
                else:
                    return 0
            except Exception, e:
                return 0

    # Delete domain.
    @decorators.require_global_admin
    def delete(self, domains=[]):
        if not isinstance(domains, types.ListType):
            return (False, 'INVALID_DOMAIN_NAME')

        msg = {}
        for domain in domains:
            if not iredutils.isDomain(domain):
                continue

            dn = ldaputils.convKeywordToDN(web.safestr(domain), accountType='domain')
        
            try:
                deltree.DelTree(self.conn, dn, ldap.SCOPE_SUBTREE)
                web.logger(msg="Delete domain: %s." % (domain), domain=domain, event='delete',)
            except ldap.LDAPError, e:
                msg[domain] = str(e)

            # Delete records from SQL database: real-time used quota.
            if session.get('enableShowUsedQuota', False) is True:
                try:
                    # SQL: DELETE FROM table WHERE username LIKE '%@domain.ltd'
                    web.admindb.delete(
                        models.UsedQuota.__table__,
                        where='%s LIKE %s' % (
                            models.UsedQuota.username,
                            web.sqlquote('%%@'+domain),
                        ),
                    )
                except Exception, e:
                    pass

        if msg == {}:
            return (True,)
        else:
            return (False, ldaputils.getExceptionDesc(msg))

    @decorators.require_global_admin
    def enableOrDisableAccount(self, domains, action, attr='accountStatus',):
        if domains is None or len(domains) == 0:
            return (False, 'NO_DOMAIN_SELECTED')

        result = {}
        connutils = connUtils.Utils()
        for domain in domains:
            self.domain = web.safestr(domain)
            self.dn = ldaputils.convKeywordToDN(self.domain, accountType='domain')

            try:
                connutils.enableOrDisableAccount(
                    domain=self.domain,
                    account=self.domain,
                    dn=self.dn,
                    action=web.safestr(action).strip().lower(),
                    accountTypeInLogger='domain',
                )
            except ldap.LDAPError, e:
                result[self.domain] = str(e)

        if result == {}:
            return (True,)
        else:
            return (False, ldaputils.getExceptionDesc(result))

    # Get domain attributes & values.
    @decorators.require_domain_access
    def profile(self, domain):
        self.domain = web.safestr(domain)
        self.dn = ldaputils.convKeywordToDN(self.domain, accountType='domain')

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
            return (False, ldaputils.getExceptionDesc(e))

    # Update domain profile.
    # data = web.input()
    def update(self, profile_type, domain, data):
        self.profile_type = web.safestr(profile_type)
        self.domain = web.safestr(domain)
        self.domaindn = ldaputils.convKeywordToDN(self.domain, accountType='domain')

        connutils = connUtils.Utils()
        self.accountSetting = []
        mod_attrs = []

        # Allow normal admin to update profiles.
        if self.profile_type == 'general':
            cn = data.get('cn', None)
            mod_attrs += ldaputils.getSingleModAttr(attr='cn', value=cn, default=self.domain)
        else:
            pass

        # Allow global admin to update profiles.
        if session.get('domainGlobalAdmin') is True:
            if self.profile_type == 'general':
                # Get accountStatus.
                if 'accountStatus' in data.keys():
                    accountStatus = 'active'
                else:
                    accountStatus = 'disabled'

                mod_attrs += [ (ldap.MOD_REPLACE, 'accountStatus', accountStatus) ]
            else:
                pass

        else:
            pass

        try:
            dn = ldaputils.convKeywordToDN(self.domain, accountType='domain')
            self.conn.modify_s(dn, mod_attrs)
            return (True,)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    @decorators.require_domain_access
    def getDomainAccountSetting(self, domain,):
        result = self.getAllDomains(
            filter='(&(objectClass=mailDomain)(domainName=%s))' % domain,
            attrs=['domainName', 'accountSetting',],
        )

        if result[0] is True:
            allDomains = result[1]
        else:
            return result

        # Get accountSetting of current domain.
        try:
            allAccountSettings = ldaputils.getAccountSettingFromLdapQueryResult(allDomains, key='domainName')
            return (True, allAccountSettings.get(domain, {}))
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))
