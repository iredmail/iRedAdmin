# Author: Zhang Huangbin <zhb@iredmail.org>

import time
import ldap
import web

import settings
from libs import iredutils
from libs.ldaplib import core, attrs, iredldif, ldaputils, deltree, connUtils, decorators

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
        if not iredutils.is_domain(self.domain):
            return (False, 'INVALID_DOMAIN_NAME')

        # Check whether domain name already exist (domainName, domainAliasName).
        connutils = connUtils.Utils()
        if connutils.is_domain_exists(self.domain):
            return (False, 'ALREADY_EXISTS')

        self.dn = ldaputils.convert_keyword_to_dn(self.domain, accountType='domain')
        if self.dn[0] is False:
            return self.dn

        self.cn = data.get('cn', None)
        ldif = iredldif.ldif_maildomain(domain=self.domain, cn=self.cn,)

        # Add domain dn.
        try:
            self.conn.add_s(self.dn, ldif)
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
        dn = ldaputils.convert_keyword_to_dn(domain, accountType='domain')
        if dn[0] is False:
            return dn

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
        self.dn = ldaputils.convert_keyword_to_dn(self.domain, accountType='domain')
        if self.dn[0] is False:
            return self.dn

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
            except Exception:
                return 0

    # Delete domain.
    @decorators.require_global_admin
    def delete(self, domains=None, keep_mailbox_days=0):
        if not domains:
            return (False, 'INVALID_DOMAIN_NAME')

        domains = [str(v).lower() for v in domains if iredutils.is_domain(v)]

        if not domains:
            return (True, )

        msg = {}
        for domain in domains:
            dn = ldaputils.convert_keyword_to_dn(web.safestr(domain), accountType='domain')
            if dn[0] is False:
                return dn

            # Log maildir path in SQL table.
            try:
                qr = self.conn.search_s(attrs.DN_BETWEEN_USER_AND_DOMAIN + dn,
                                        ldap.SCOPE_ONELEVEL,
                                        "(objectClass=mailUser)",
                                        ['mail', 'homeDirectory'])

                if keep_mailbox_days == 0:
                    keep_mailbox_days = 36500

                # Convert keep days to string
                _now_in_seconds = time.time()
                _days_in_seconds = _now_in_seconds + (keep_mailbox_days * 24 * 60 * 60)
                sql_keep_days = time.strftime('%Y-%m-%d', time.strptime(time.ctime(_days_in_seconds)))

                v = []
                for obj in qr:
                    deleted_mail = obj[1].get('mail')[0]
                    deleted_maildir = obj[1].get('homeDirectory', [''])[0]
                    v += [{'maildir': deleted_maildir,
                           'username': deleted_mail,
                           'domain': domain,
                           'admin': session.get('username'),
                           'delete_date': sql_keep_days}]

                if v:
                    web.admindb.multiple_insert('deleted_mailboxes', values=v)
            except:
                pass

            try:
                deltree.DelTree(self.conn, dn, ldap.SCOPE_SUBTREE)
                web.logger(msg="Delete domain: %s." % (domain), domain=domain, event='delete',)
            except ldap.LDAPError, e:
                msg[domain] = str(e)

        # Delete real-time mailbox quota.
        try:
            web.admindb.query('DELETE FROM %s WHERE %s' % (settings.SQL_TBL_USED_QUOTA,
                                                           web.sqlors('username LIKE ', ['%@' + d for d in domains])))
        except:
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
            self.dn = ldaputils.convert_keyword_to_dn(self.domain, accountType='domain')
            if self.dn[0] is False:
                return self.dn

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
        self.dn = ldaputils.convert_keyword_to_dn(self.domain, accountType='domain')
        if self.dn[0] is False:
            return self.dn

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
        self.domaindn = ldaputils.convert_keyword_to_dn(self.domain, accountType='domain')
        if self.domaindn[0] is False:
            return self.domaindn

        self.accountSetting = []
        mod_attrs = []

        # Allow normal admin to update profiles.
        if self.profile_type == 'general':
            cn = data.get('cn', None)
            mod_attrs += ldaputils.getSingleModAttr(attr='cn', value=cn, default=self.domain)

        # Allow global admin to update profiles.
        if session.get('domainGlobalAdmin') is True:
            if self.profile_type == 'general':
                # Get accountStatus.
                if 'accountStatus' in data.keys():
                    accountStatus = 'active'
                else:
                    accountStatus = 'disabled'

                mod_attrs += [(ldap.MOD_REPLACE, 'accountStatus', accountStatus)]

        try:
            dn = ldaputils.convert_keyword_to_dn(self.domain, accountType='domain')
            if dn[0] is False:
                return dn

            self.conn.modify_s(dn, mod_attrs)
            web.logger(msg="Update domain profile: %s (%s)." % (domain, profile_type),
                       domain=domain,
                       event='update')
            return (True,)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    @decorators.require_domain_access
    def getDomainAccountSetting(self, domain,):
        result = self.getAllDomains(
            filter='(&(objectClass=mailDomain)(domainName=%s))' % domain,
            attrs=['domainName', 'accountSetting', ],
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
