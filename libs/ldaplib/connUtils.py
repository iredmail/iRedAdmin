# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import ldap
from ldap.filter import escape_filter_chars
import settings
from libs import iredutils
from libs.ldaplib import core, ldaputils, decorators, attrs, deltree

session = web.config.get('_session')


class Utils(core.LDAPWrap):
    def __del__(self):
        try:
            self.conn.unbind()
        except:
            pass

    def addOrDelAttrValue(self, dn, attr, value, action):
        """Used to add or delete value of attribute which can handle multiple values.

        @attr: ldap attribute name
        @value: value of attr
        @action: add, delete.
        """
        dn = escape_filter_chars(dn)
        if isinstance(value, list):
            values = value
        else:
            values = [value]

        msg = ''
        if action in ['add', 'assign', 'enable']:
            for v in values:
                try:
                    self.conn.modify_s(dn, [(ldap.MOD_ADD, attr, v)])
                except (ldap.NO_SUCH_OBJECT, ldap.TYPE_OR_VALUE_EXISTS):
                    pass
                except Exception, e:
                    msg += str(e)
        elif action in ['del', 'delete', 'remove', 'disable']:
            #
            # Note
            #
            # OpenBSD ldapd(*) cannot handle MOD_DELETE correctly, it will
            # remove all values of this attribute instead of removing just the
            # one we specified.
            #
            # As a workaround, we perform one extra LDAP query to get all
            # present values of the attribute first, then remove the one we
            # want to delete.
            if settings.LDAP_SERVER_PRODUCT_NAME == 'LDAPD':
                try:
                    # Get present values
                    qr = self.conn.search_s(dn, ldap.SCOPE_BASE, attrlist=[attr])
                    entries = qr[0][1].get(attr, [])
                    entries_new = set(entries)

                    for v in values:
                        if v in entries_new:
                            entries_new.remove(v)

                    if entries_new:
                        mod_attr = [(ldap.MOD_REPLACE, attr, list(entries_new))]
                    else:
                        # Delete thie attribute if no value left.
                        mod_attr = [(ldap.MOD_REPLACE, attr, None)]

                    self.conn.modify_s(dn, mod_attr)
                except ldap.NO_SUCH_ATTRIBUTE:
                    pass
                except Exception, e:
                    msg += str(e)
            else:
                # OpenLDAP
                for v in values:
                    try:
                        self.conn.modify_s(dn, [(ldap.MOD_DELETE, attr, str(v))])
                    except ldap.NO_SUCH_ATTRIBUTE:
                        pass
                    except Exception, e:
                        msg += str(e)
        else:
            return (False, 'UNKNOWN_ACTION')

        if len(msg) == 0:
            return (True,)
        else:
            return (False, msg)

    # Change password.
    def changePasswd(self, dn, cur_passwd, newpw):
        dn = escape_filter_chars(dn)
        try:
            # Reference: RFC3062 - LDAP Password Modify Extended Operation
            self.conn.passwd_s(dn, cur_passwd, newpw)
            return (True,)
        except ldap.UNWILLING_TO_PERFORM:
            return (False, 'INCORRECT_OLDPW')
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    # Update value of attribute which must be single value.
    def updateAttrSingleValue(self, dn, attr, value):
        self.mod_attrs = [(ldap.MOD_REPLACE, web.safestr(attr), web.safestr(value))]
        try:
            self.conn.modify_s(web.safestr(dn), self.mod_attrs)
            return (True,)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    # Get number of current accounts.
    def getNumberOfCurrentAccountsUnderDomain(self, domain, accountType='user', filter=None):
        # accountType in ['user', 'list', 'alias',]
        self.domain = web.safestr(domain)
        self.domaindn = ldaputils.convert_keyword_to_dn(self.domain, accountType='domain')

        if filter is not None:
            self.searchdn = self.domaindn
            self.filter = filter
        else:
            if accountType == 'user':
                self.searchdn = attrs.DN_BETWEEN_USER_AND_DOMAIN + self.domaindn
                self.filter = '(&(objectClass=mailUser)(!(mail=@%s)))' % self.domain
            else:
                self.searchdn = self.domaindn
                self.filter = '(&(objectClass=mailUser)(!(mail=@%s)))' % self.domain

        try:
            result = self.conn.search_s(
                self.searchdn,
                ldap.SCOPE_SUBTREE,
                self.filter,
                ['dn', ],
            )
            return (True, len(result))
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    # Check whether domain name already exist (domainName, domainAliasName).
    def is_domain_exists(self, domain):
        # Return True if account is invalid or exist.
        self.domain = web.safestr(domain).strip().lower()

        # Check domain name.
        if not iredutils.is_domain(self.domain):
            # Return True if invalid.
            return True

        # Check domainName and domainAliasName.
        try:
            result = self.conn.search_s(
                settings.ldap_basedn,
                ldap.SCOPE_ONELEVEL,
                '(|(domainName=%s)(domainAliasName=%s))' % (self.domain, self.domain),
                ['domainName', 'domainAliasName', ],
            )
            if len(result) > 0:
                # Domain name exist.
                return True
            else:
                return False
        except:
            return True

    # Check whether account exist or not.
    def isAccountExists(self, domain, mail,):
        # Return True if account is invalid or exist.
        self.domain = str(domain)
        self.mail = str(mail)

        if not iredutils.is_domain(self.domain):
            return True

        if not iredutils.is_email(self.mail):
            return True

        # Check whether mail address ends with domain name or alias domain name.
        self.mail_domain = self.mail.split('@', 1)[-1]
        qr_domain_and_aliases = self.getAvailableDomainNames(self.domain)
        if qr_domain_and_aliases[0] is True:
            if self.mail_domain not in qr_domain_and_aliases[1]:
                # Mail address is invalid.
                return True

        # Filter used to search mail accounts.
        ldap_filter = '(&(|(objectClass=mailUser)(objectClass=mailList)(objectClass=mailAlias))(|(mail=%s)(shadowAddress=%s)))' % (self.mail, self.mail)

        try:
            self.number = self.getNumberOfCurrentAccountsUnderDomain(
                domain=self.domain,
                filter=ldap_filter,
            )

            if self.number[0] is True and self.number[1] == 0:
                # Account not exist.
                return False
            else:
                return True
        except:
            # Account 'EXISTS' (fake) if ldap lookup failed.
            return True

    @decorators.require_domain_access
    def enableOrDisableAccount(self, domain, account, dn, action, accountTypeInLogger=None):
        self.domain = web.safestr(domain).strip().lower()
        self.account = web.safestr(account).strip().lower()
        self.dn = escape_filter_chars(web.safestr(dn))

        # Validate operation action.
        if action in ['enable', 'disable', ]:
            self.action = action
        else:
            return (False, 'INVALID_ACTION')

        # Set value of valid account status.
        if action == 'enable':
            self.status = attrs.ACCOUNT_STATUS_ACTIVE
        else:
            self.status = attrs.ACCOUNT_STATUS_DISABLED

        try:
            self.updateAttrSingleValue(
                dn=self.dn,
                attr='accountStatus',
                value=self.status,
            )

            if accountTypeInLogger is not None:
                web.logger(
                    msg="%s %s: %s." % (str(action).capitalize(), str(accountTypeInLogger), self.account),
                    domain=self.domain,
                    event=self.action,
                )

            return (True,)
        except ldap.LDAPError, e:
            return (False, ldaputils.getExceptionDesc(e))

    @decorators.require_domain_access
    def deleteObjWithDN(self, domain, dn, account, accountType,):
        self.domain = web.safestr(domain)
        if not iredutils.is_domain(self.domain):
            return (False, 'INVALID_DOMAIN_NAME')

        self.dn = escape_filter_chars(dn)

        # Used for logger.
        self.account = web.safestr(account)

        try:
            deltree.DelTree(self.conn, self.dn, ldap.SCOPE_SUBTREE)
            web.logger(
                msg="Delete %s: %s." % (str(accountType), self.account),
                domain=self.domain,
                event='delete',
            )

            return (True,)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    def getSizelimitFromAccountLists(self, accountList, sizelimit=50, curPage=1, domain=None, accountType=None,):
        # Return a dict which contains:
        #   - totalAccounts: number of total accounts
        #   - accountList: list of accounts used to display in current page
        #   - totalPages: number of total pages show be showed in account list page.
        #   - totalQuota: number of domain quota size. Only available when accountType=='user'.

        # Initial a dict to set default values.
        result = {
            'totalAccounts': 0,         # Integer
            'accountList': [],          # List
            'totalPages': 0,            # Integer
            'totalQuota': 0,            # Integer
            'currentQuota': {},     # Dict
        }

        # Get total accounts.
        totalAccounts = len(accountList)
        result['totalAccounts'] = totalAccounts

        # Get number of actual pages.
        if totalAccounts % sizelimit == 0:
            totalPages = totalAccounts / sizelimit
        else:
            totalPages = (totalAccounts / sizelimit) + 1
        result['totalPages'] = totalPages

        if curPage >= totalPages:
            curPage = totalPages

        # Sort accounts in place.
        if isinstance(accountList, list):
            accountList.sort()
        else:
            pass

        # Get total domain mailbox quota.
        if accountType == 'user':
            counter = 0
            for i in accountList:
                quota = i[1].get('mailQuota', ['0'])[0]
                if quota.isdigit():
                    result['totalQuota'] += int(quota)
                    counter += 1

            # Update number of current domain quota size in LDAP (@attrs.ATTR_DOMAIN_CURRENT_QUOTA_SIZE).
            if domain is not None:
                # Update number of current domain quota size in LDAP.
                try:
                    dnDomain = ldaputils.convert_keyword_to_dn(domain, accountType='domain')
                    self.updateAttrSingleValue(
                        dn=dnDomain,
                        attr=attrs.ATTR_DOMAIN_CURRENT_QUOTA_SIZE,
                        value=str(result['totalQuota']),
                    )
                except:
                    pass

        # Get account list used to display in current page.
        if totalAccounts > sizelimit and totalAccounts < (curPage - 1) * sizelimit:
            accountList = accountList[-1:-sizelimit]
        else:
            accountList = accountList[(curPage - 1) * sizelimit: (curPage - 1) * sizelimit + sizelimit]
        result['accountList'] = accountList

        return result

    @decorators.require_domain_access
    def getDomainCurrentQuotaSizeFromLDAP(self, domain):
        self.domain = web.safestr(domain).strip().lower()
        if not iredutils.is_domain(self.domain):
            return (False, 'INVALID_DOMAIN_NAME')

        self.domainDN = ldaputils.convert_keyword_to_dn(self.domain, accountType='domain')

        # Initial @domainCurrentQuotaSize
        self.domainCurrentQuotaSize = 0

        try:
            # Use '(!(mail=@domain.ltd))' to hide catch-all account.
            self.users = self.conn.search_s(
                attrs.DN_BETWEEN_USER_AND_DOMAIN + self.domainDN,
                ldap.SCOPE_SUBTREE,
                '(&(objectClass=mailUser)(!(mail=@%s)))' % self.domain,
                attrs.USER_SEARCH_ATTRS,
            )

            # Update @domainCurrentUserNumber
            self.updateAttrSingleValue(self.domainDN, 'domainCurrentUserNumber', len(self.users))

            for i in self.users:
                quota = i[1].get('mailQuota', ['0'])[0]
                if quota.isdigit():
                    self.domainCurrentQuotaSize += int(quota)
            return (True, self.domainCurrentQuotaSize)
        except ldap.NO_SUCH_OBJECT:
            return (False, 'NO_SUCH_OBJECT')
        except ldap.SIZELIMIT_EXCEEDED:
            return (False, 'EXCEEDED_LDAP_SERVER_SIZELIMIT')
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    @decorators.require_domain_access
    def getAvailableDomainNames(self, domain):
        '''Get list of domainName and domainAliasName by quering domainName.

        >>> getAvailableDomainNames(domain='example.com')
        (True, ['example.com', 'aliasdomain01.com', 'aliasdomain02.com', ...])
        '''
        domain = web.safestr(domain).strip().lower()
        if not iredutils.is_domain(domain):
            return (False, 'INVALID_DOMAIN_NAME')

        dn = ldaputils.convert_keyword_to_dn(domain, accountType='domain')

        try:
            result = self.conn.search_s(
                dn,
                ldap.SCOPE_BASE,
                '(&(objectClass=mailDomain)(domainName=%s))' % domain,
                ['domainName', 'domainAliasName'],
            )

            all_domains = result[0][1].get('domainName', []) + result[0][1].get('domainAliasName', [])
            all_domains = [str(d).lower() for d in all_domains if iredutils.is_domain(d)]
            return (True, all_domains)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    def getDnWithKeyword(self, value, accountType='user'):
        self.keyword = web.safestr(value)

        if accountType == 'user':
            if attrs.RDN_USER == 'mail':
                if not iredutils.is_email(self.keyword):
                    return False
                return ldaputils.convert_keyword_to_dn(self.keyword, accountType='user')
            else:
                self.domain = self.keyword.split('@', 1)[-1]
                self.dnOfDomain = ldaputils.convert_keyword_to_dn(self.domain, accountType='domain',)
                try:
                    result = self.conn.search_s(
                        attrs.DN_BETWEEN_USER_AND_DOMAIN + self.dnOfDomain,
                        ldap.SCOPE_SUBTREE,
                        '(&(objectClass=mailUser)(mail=%s))' % (self.keyword),
                    )
                    if len(result) == 1:
                        self.dn = result[0][0]
                        return self.dn
                    else:
                        return False
                except:
                    return False
        else:
            # Unsupported accountType.
            return False

    # Get domains under control.
    def getManagedDomains(self, mail, attrs=attrs.ADMIN_ATTRS_ALL, listedOnly=False):
        self.mail = web.safestr(mail)
        if not iredutils.is_email(self.mail):
            return (False, 'INCORRECT_USERNAME')

        # Pre-defined filter.
        filter = '(&(objectClass=mailDomain)(domainAdmin=%s))' % self.mail
        if session.get('domainGlobalAdmin') is True and listedOnly is False:
            filter = '(objectClass=mailDomain)'

        try:
            self.managedDomains = self.conn.search_s(
                self.basedn,
                ldap.SCOPE_ONELEVEL,
                filter,
                attrs,
            )
            if listedOnly:
                domains = []
                for qr in self.managedDomains:
                    domains += qr[1]['domainName']
                self.managedDomains = domains
            return (True, self.managedDomains)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))


def deleteAccountFromUsedQuota(accounts):
    # @accounts: must be list/tuple of email addresses.
    if not isinstance(accounts, (list, tuple)):
        return (False, 'INVALID_MAIL')

    if accounts:
        try:
            web.admindb.delete(
                settings.SQL_TBL_USED_QUOTA,
                vars={'accounts': accounts},
                where='username IN $accounts',
            )
            return (True,)
        except Exception, e:
            return (False, str(e))
    else:
        return (True,)
