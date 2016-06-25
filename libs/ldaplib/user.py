# Author: Zhang Huangbin <zhb@iredmail.org>

import os
import time
import ldap
import ldap.filter
import web
import settings
from libs import iredutils
from libs.ldaplib import core, domain as domainlib, attrs, ldaputils, iredldif, connUtils, decorators, deltree

session = web.config.get('_session')


class User(core.LDAPWrap):
    def __del__(self):
        try:
            self.conn.unbind()
        except:
            pass

    # List all users under one domain.
    @decorators.require_domain_access
    def listAccounts(self, domain):
        self.domain = domain
        self.domainDN = ldaputils.convert_keyword_to_dn(self.domain, accountType='domain')
        if self.domainDN[0] is False:
            return self.domainDN

        try:
            # Use '(!(mail=@domain.ltd))' to hide catch-all account.
            self.users = self.conn.search_s(
                attrs.DN_BETWEEN_USER_AND_DOMAIN + self.domainDN,
                ldap.SCOPE_SUBTREE,
                '(&(objectClass=mailUser)(!(mail=@%s)))' % self.domain,
                attrs.USER_SEARCH_ATTRS,
            )

            connutils = connUtils.Utils()
            connutils.updateAttrSingleValue(self.domainDN, 'domainCurrentUserNumber', len(self.users))

            return (True, self.users)
        except ldap.NO_SUCH_OBJECT:
            return (False, 'NO_SUCH_OBJECT')
        except ldap.SIZELIMIT_EXCEEDED:
            return (False, 'EXCEEDED_LDAP_SERVER_SIZELIMIT')
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    # Get values of user or domain catch-all account.
    # accountType in ['user', 'catchall',]
    @decorators.require_domain_access
    def profile(self, domain, mail, accountType='user'):
        self.mail = web.safestr(mail)
        self.domain = self.mail.split('@', 1)[-1]

        if self.domain != domain:
            raise web.seeother('/domains?msg=PERMISSION_DENIED')

        self.filter = '(&(objectClass=mailUser)(mail=%s))' % (self.mail)
        if accountType == 'catchall':
            self.filter = '(&(objectClass=mailUser)(mail=@%s))' % (self.mail)
        else:
            if not self.mail.endswith('@' + self.domain):
                raise web.seeother('/domains?msg=PERMISSION_DENIED')

        if attrs.RDN_USER == 'mail':
            self.searchdn = ldaputils.convert_keyword_to_dn(self.mail, accountType=accountType)
            self.scope = ldap.SCOPE_BASE

            if self.searchdn[0] is False:
                return self.searchdn
        else:
            domain_dn = ldaputils.convert_keyword_to_dn(self.domain, accountType='domain')
            if domain_dn[0] is False:
                return domain_dn

            self.searchdn = attrs.DN_BETWEEN_USER_AND_DOMAIN + domain_dn
            self.scope = ldap.SCOPE_SUBTREE

        try:
            self.user_profile = self.conn.search_s(
                self.searchdn,
                self.scope,
                self.filter,
                attrs.USER_ATTRS_ALL,
            )
            return (True, self.user_profile)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    @decorators.require_domain_access
    def add(self, domain, data):
        # Get domain name, username, cn.
        self.domain = web.safestr(data.get('domainName')).strip().lower()
        self.username = web.safestr(data.get('username')).strip().lower()
        self.mail = self.username + '@' + self.domain
        self.groups = data.get('groups', [])

        if not iredutils.is_domain(self.domain) or not iredutils.is_email(self.mail):
            return (False, 'MISSING_DOMAIN_OR_USERNAME')

        # Check account existing.
        connutils = connUtils.Utils()
        if connutils.isAccountExists(domain=self.domain, mail=self.mail):
            return (False, 'ALREADY_EXISTS')

        # Get @domainAccountSetting.
        domainLib = domainlib.Domain()
        result_domain_profile = domainLib.profile(domain=self.domain)

        # Initial parameters.
        domainAccountSetting = {}
        self.aliasDomains = []

        if result_domain_profile[0] is not True:
            return (False, result_domain_profile[1])

        domainProfile = result_domain_profile[1]
        domainAccountSetting = ldaputils.getAccountSettingFromLdapQueryResult(domainProfile, key='domainName').get(self.domain, {})
        self.aliasDomains = domainProfile[0][1].get('domainAliasName', [])

        # Check account number limit.
        numberOfAccounts = domainAccountSetting.get('numberOfUsers')
        if numberOfAccounts == '-1':
            return (False, 'NOT_ALLOWED')

        # Check password.
        self.newpw = web.safestr(data.get('newpw'))
        self.confirmpw = web.safestr(data.get('confirmpw'))

        result = iredutils.verify_new_password(
            self.newpw,
            self.confirmpw,
            min_passwd_length=domainAccountSetting.get('minPasswordLength', '0'),
            max_passwd_length=domainAccountSetting.get('maxPasswordLength', '0'),
        )
        if result[0] is True:
            if 'storePasswordInPlainText' in data and settings.STORE_PASSWORD_IN_PLAIN_TEXT:
                self.passwd = iredutils.generate_password_hash(result[1], pwscheme='PLAIN')
            else:
                self.passwd = iredutils.generate_password_hash(result[1])
        else:
            return result

        # Get display name.
        self.cn = data.get('cn')

        # Get user quota. Unit is MB.
        # 0 or empty is not allowed if domain quota is set, set to
        # @defaultUserQuota or @domainSpareQuotaSize

        # Initial final mailbox quota.
        self.quota = 0

        # Get mail quota from web form.
        defaultUserQuota = domainLib.getDomainDefaultUserQuota(self.domain, domainAccountSetting)
        self.mailQuota = str(data.get('mailQuota')).strip()
        if self.mailQuota.isdigit():
            self.mailQuota = int(self.mailQuota)
        else:
            self.mailQuota = defaultUserQuota

        # 0 means unlimited.
        domainQuotaSize, domainQuotaUnit = domainAccountSetting.get('domainQuota', '0:GB').split(':')
        if int(domainQuotaSize) == 0:
            # Unlimited.
            self.quota = self.mailQuota
        else:
            # Get domain quota, convert to MB.
            if domainQuotaUnit == 'TB':
                domainQuota = int(domainQuotaSize) * 1024 * 1024  # TB
            elif domainQuotaUnit == 'GB':
                domainQuota = int(domainQuotaSize) * 1024  # GB
            else:
                domainQuota = int(domainQuotaSize)  # MB

            result = connutils.getDomainCurrentQuotaSizeFromLDAP(domain=self.domain)
            if result[0] is True:
                domainCurrentQuotaSize = result[1]
            else:
                domainCurrentQuotaSize = 0

            # Spare quota.
            domainSpareQuotaSize = domainQuota - domainCurrentQuotaSize / (1024 * 1024)

            if domainSpareQuotaSize <= 0:
                return (False, 'EXCEEDED_DOMAIN_QUOTA_SIZE')

            # Get FINAL mailbox quota.
            if self.mailQuota == 0:
                self.quota = domainSpareQuotaSize
            else:
                if domainSpareQuotaSize > self.mailQuota:
                    self.quota = self.mailQuota
                else:
                    self.quota = domainSpareQuotaSize

        # Get default groups.
        self.groups = [web.safestr(v)
                       for v in domainAccountSetting.get('defaultList', '').split(',')
                       if iredutils.is_email(v)]

        self.defaultStorageBaseDirectory = domainAccountSetting.get('defaultStorageBaseDirectory', None)

        # Get default mail lists which set in domain accountSetting.
        ldif = iredldif.ldif_mailuser(
            domain=self.domain,
            aliasDomains=self.aliasDomains,
            username=self.username,
            cn=self.cn,
            passwd=self.passwd,
            quota=self.quota,
            groups=self.groups,
            storageBaseDirectory=self.defaultStorageBaseDirectory,
        )

        domain_dn = ldaputils.convert_keyword_to_dn(self.domain, accountType='domain')
        if domain_dn[0] is False:
            return domain_dn

        if attrs.RDN_USER == 'mail':
            self.dn = ldaputils.convert_keyword_to_dn(self.mail, accountType='user')
            if self.dn[0] is False:
                return self.dn

        elif attrs.RDN_USER == 'cn':
            self.dn = 'cn=' + self.cn + ',' + attrs.DN_BETWEEN_USER_AND_DOMAIN + domain_dn
        elif attrs.RDN_USER == 'uid':
            self.dn = 'uid=' + self.username + ',' + attrs.DN_BETWEEN_USER_AND_DOMAIN + domain_dn
        else:
            return (False, 'UNSUPPORTED_USER_RDN')

        try:
            self.conn.add_s(ldap.filter.escape_filter_chars(self.dn), ldif)
            web.logger(msg="Create user: %s." % (self.mail), domain=self.domain, event='create')
            return (True, )
        except ldap.ALREADY_EXISTS:
            return (False, 'ALREADY_EXISTS')
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    def getFilterOfDeleteUserFromGroups(self, mail):
        # Get valid emails as list.
        if isinstance(mail, list):
            self.mails = [web.safestr(v).lower() for v in mail if iredutils.is_email(str(v))]
        else:
            # Single email.
            self.mails = [web.safestr(mail).lower()]

        filterUserAndAlias = '(&(|(objectClass=mailAlias)(objectClass=mailUser))(|'
        filterExternalUser = '(&(objectClass=mailExternalUser)(|'

        for mail in self.mails:
            filterUserAndAlias += '(mailForwardingAddress=%s)' % mail
            filterExternalUser += '(mail=%s)' % mail

        # Close filter string.
        filterUserAndAlias += '))'
        filterExternalUser += '))'

        filter = '(|' + filterUserAndAlias + filterExternalUser + ')'
        return filter

    # Delete single user from mail list, alias, user forwarding addresses.
    def deleteSingleUserFromGroups(self, mail):
        self.mail = web.safestr(mail)
        if not iredutils.is_email(self.mail):
            return (False, 'INVALID_MAIL')

        # Get domain name of this account.
        self.domain = self.mail.split('@')[-1]

        # Get dn of mail user and domain.
        self.dnUser = ldaputils.convert_keyword_to_dn(self.mail, accountType='user')
        self.dnDomain = ldaputils.convert_keyword_to_dn(self.domain, accountType='domain')

        if self.dnUser[0] is False:
            return self.dnUser

        if self.dnDomain[0] is False:
            return self.dnDomain

        try:
            # Get accounts which contains destination email.
            objsHasUser = self.conn.search_s(
                self.dnDomain,
                ldap.SCOPE_SUBTREE,
                self.getFilterOfDeleteUserFromGroups(self.mail),
                ['dn'],
            )

            if len(objsHasUser) >= 1:
                connutils = connUtils.Utils()
                for obj in objsHasUser:
                    if obj[0].endswith(attrs.DN_BETWEEN_ALIAS_AND_DOMAIN + self.dnDomain) or \
                       obj[0].endswith(attrs.DN_BETWEEN_USER_AND_DOMAIN + self.dnDomain):
                        # Remove address from alias and user.
                        connutils.addOrDelAttrValue(
                            dn=obj[0],
                            attr='mailForwardingAddress',
                            value=self.mail,
                            action='delete',
                        )
                    elif obj[0].endswith('ou=Externals,' + self.domaindn):
                        # Remove address from external member list.
                        connutils.addOrDelAttrValue(
                            dn=obj[0],
                            attr='mail',
                            value=self.mail,
                            action='delete',
                        )
                    else:
                        pass
            else:
                pass

            return (True, )
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    # Delete single user.
    def deleteSingleUser(self, mail, deleteFromGroups=True, keep_mailbox_days=0):
        self.mail = web.safestr(mail)
        if not iredutils.is_email(self.mail):
            return (False, 'INVALID_MAIL')

        # Get domain name of this account.
        self.domain = self.mail.split('@')[-1]

        # Get dn of mail user and domain.
        self.dnUser = ldaputils.convert_keyword_to_dn(self.mail, accountType='user')
        if self.dnUser[0] is False:
            return self.dnUser

        # Log maildir path in SQL table.
        try:
            qr_profile = self.profile(domain=self.domain, mail=self.mail)
            if qr_profile[0]:
                user_profile = qr_profile[1][0][1]
            else:
                return qr_profile

            if 'homeDirectory' in user_profile:
                maildir = user_profile.get('homeDirectory', [''])[0]
            else:
                storageBaseDirectory = user_profile.get('storageBaseDirectory', [''])[0]
                mailMessageStore = user_profile.get('mailMessageStore', [''])[0]
                maildir = os.path.join(storageBaseDirectory, mailMessageStore)

            if keep_mailbox_days == 0:
                keep_mailbox_days = 36500

            # Convert keep days to string
            _now_in_seconds = time.time()
            _days_in_seconds = _now_in_seconds + (keep_mailbox_days * 24 * 60 * 60)
            sql_keep_days = time.strftime('%Y-%m-%d', time.strptime(time.ctime(_days_in_seconds)))

            web.admindb.insert('deleted_mailboxes',
                               maildir=maildir,
                               username=self.mail,
                               domain=self.domain,
                               admin=session.get('username'),
                               delete_date=sql_keep_days)
        except:
            pass

        del maildir

        # Delete user object.
        try:
            # Delete object and its subtree.
            deltree.DelTree(self.conn, self.dnUser, ldap.SCOPE_SUBTREE)

            if deleteFromGroups:
                self.deleteSingleUserFromGroups(self.mail)

            # Delete record from SQL database: real-time used quota.
            try:
                connUtils.deleteAccountFromUsedQuota([self.mail])
            except Exception, e:
                pass

            # Log delete action.
            web.logger(msg="Delete user: %s." % (self.mail),
                       domain=self.domain,
                       event='delete')
            return (True, )
        except ldap.LDAPError, e:
            return (False, ldaputils.getExceptionDesc(e))

    # Delete mail users in same domain.
    @decorators.require_domain_access
    def delete(self, domain, mails=None, keep_mailbox_days=0):
        if not mails:
            return (False, 'NO_ACCOUNT_SELECTED')

        self.domain = web.safestr(domain)
        self.mails = [str(v) for v in mails if iredutils.is_email(v) and str(v).endswith('@' + self.domain)]
        if not len(self.mails) > 0:
            return (False, 'INVALID_MAIL')

        if not iredutils.is_domain(self.domain):
            return (False, 'INVALID_DOMAIN_NAME')

        self.domaindn = ldaputils.convert_keyword_to_dn(self.domain, accountType='domain')

        result = {}
        for mail in self.mails:
            self.mail = web.safestr(mail)

            try:
                # Delete user object (ldap.SCOPE_BASE).
                self.deleteSingleUser(mail=self.mail, keep_mailbox_days=keep_mailbox_days)

                # Delete user object and whole sub-tree.
                # Get dn of mail user and domain.
                """
                self.userdn = ldaputils.convert_keyword_to_dn(self.mail, accountType='user')
                deltree.DelTree(self.conn, self.userdn, ldap.SCOPE_SUBTREE)

                # Log delete action.
                web.logger(
                    msg="Delete user: %s." % (self.mail),
                    domain=self.mail.split('@')[1],
                    event='delete',
                )
                """
            except ldap.LDAPError, e:
                result[self.mail] = ldaputils.getExceptionDesc(e)

        if result == {}:
            return (True, )
        else:
            return (False, str(result))

    @decorators.require_domain_access
    def enableOrDisableAccount(self, domain, mails, action, attr='accountStatus'):
        if mails is None or len(mails) == 0:
            return (False, 'NO_ACCOUNT_SELECTED')

        self.mails = [str(v)
                      for v in mails
                      if iredutils.is_email(v) and str(v).endswith('@' + str(domain))]

        result = {}
        connutils = connUtils.Utils()
        for mail in self.mails:
            self.mail = web.safestr(mail)
            if not iredutils.is_email(self.mail):
                continue

            self.domain = self.mail.split('@')[-1]
            self.dn = ldaputils.convert_keyword_to_dn(self.mail, accountType='user')
            if self.dn[0] is False:
                result[self.mail] = self.dn[1]
                continue

            try:
                connutils.enableOrDisableAccount(
                    domain=self.domain,
                    account=self.mail,
                    dn=self.dn,
                    action=web.safestr(action).strip().lower(),
                    accountTypeInLogger='user',
                )
            except ldap.LDAPError, e:
                result[self.mail] = str(e)

        if result == {}:
            return (True, )
        else:
            return (False, str(result))

    @decorators.require_domain_access
    def update(self, profile_type, mail, data):
        self.profile_type = web.safestr(profile_type)
        self.mail = str(mail).lower()
        self.username, self.domain = self.mail.split('@', 1)

        domainAccountSetting = {}

        connutils = connUtils.Utils()
        domainLib = domainlib.Domain()

        # Get account dn.
        self.dn = connutils.getDnWithKeyword(self.mail, accountType='user')

        try:
            result = domainLib.getDomainAccountSetting(domain=self.domain)
            if result[0] is True:
                domainAccountSetting = result[1]
        except Exception, e:
            pass

        mod_attrs = []
        if self.profile_type == 'general':
            # Update domainGlobalAdmin=yes
            if session.get('domainGlobalAdmin') is True:
                # Update domainGlobalAdmin=yes
                if 'domainGlobalAdmin' in data:
                    mod_attrs = [(ldap.MOD_REPLACE, 'domainGlobalAdmin', 'yes')]
                    # Update enabledService=domainadmin
                    connutils.addOrDelAttrValue(
                        dn=self.dn,
                        attr='enabledService',
                        value='domainadmin',
                        action='add',
                    )
                else:
                    mod_attrs = [(ldap.MOD_REPLACE, 'domainGlobalAdmin', None)]
                    # Remove enabledService=domainadmin
                    connutils.addOrDelAttrValue(
                        dn=self.dn,
                        attr='enabledService',
                        value='domainadmin',
                        action='delete',
                    )

            # Get display name.
            cn = data.get('cn', None)
            mod_attrs += ldaputils.getSingleModAttr(attr='cn',
                                                    value=cn,
                                                    default=self.username)

            first_name = data.get('first_name', '')
            mod_attrs += ldaputils.getSingleModAttr(attr='givenName',
                                                    value=first_name,
                                                    default=self.username)

            last_name = data.get('last_name', '')
            mod_attrs += ldaputils.getSingleModAttr(attr='sn',
                                                    value=last_name,
                                                    default=self.username)

            # Get preferred language: short lang code. e.g. en_US, de_DE.
            preferred_lang = web.safestr(data.get('preferredLanguage', 'en_US'))
            # Must be equal to or less than 5 characters.
            if len(preferred_lang) > 5:
                preferred_lang = preferred_lang[:5]
            mod_attrs += [(ldap.MOD_REPLACE, 'preferredLanguage', preferred_lang)]
            # Update language immediately.
            if session.get('username') == self.mail and \
               session.get('lang', 'en_US') != preferred_lang:
                session['lang'] = preferred_lang

            # Update employeeNumber, mobile, title.
            for tmp_attr in ['employeeNumber', 'mobile', 'title', ]:
                mod_attrs += ldaputils.getSingleModAttr(attr=tmp_attr, value=data.get(tmp_attr), default=None)

            ############
            # Get quota

            # Get mail quota from web form.
            quota = web.safestr(data.get('mailQuota', '')).strip()
            oldquota = web.safestr(data.get('oldMailQuota', '')).strip()
            if not oldquota.isdigit():
                oldquota = 0
            else:
                oldquota = int(oldquota)

            if quota == '' or not quota.isdigit():
                # Don't touch it, keep original value.
                pass
            else:
                # Assign quota which got from web form.
                mailQuota = int(quota)

                # If mailQuota > domainSpareQuotaSize, use domainSpareQuotaSize.
                # if mailQuota < domainSpareQuotaSize, use mailQuota
                # 0 means unlimited.
                domainQuotaSize, domainQuotaUnit = domainAccountSetting.get('domainQuota', '0:GB').split(':')

                if int(domainQuotaSize) == 0:
                    # Unlimited. Keep quota which got from web form.
                    mod_attrs += [(ldap.MOD_REPLACE, 'mailQuota', str(mailQuota * 1024 * 1024))]
                else:
                    # Get domain quota.
                    if domainQuotaUnit == 'TB':
                        domainQuota = int(domainQuotaSize) * 1024 * 1024  # TB
                    elif domainQuotaUnit == 'GB':
                        domainQuota = int(domainQuotaSize) * 1024  # GB
                    else:
                        domainQuota = int(domainQuotaSize)  # MB

                    # Query LDAP and get current domain quota size.
                    result = connutils.getDomainCurrentQuotaSizeFromLDAP(domain=self.domain)
                    if result[0] is True:
                        domainCurrentQuotaSizeInBytes = result[1]
                    else:
                        domainCurrentQuotaSizeInBytes = 0

                    # Spare quota.
                    domainSpareQuotaSize = (domainQuota + oldquota) - (domainCurrentQuotaSizeInBytes / (1024 * 1024))

                    if domainSpareQuotaSize <= 0:
                        # Set to 1MB. don't exceed domain quota size.
                        mod_attrs += [(ldap.MOD_REPLACE, 'mailQuota', str(1024 * 1024))]
                    else:
                        # Get FINAL mailbox quota.
                        if mailQuota >= domainSpareQuotaSize:
                            mailQuota = domainSpareQuotaSize
                        mod_attrs += [(ldap.MOD_REPLACE, 'mailQuota', str(mailQuota * 1024 * 1024))]
            # End quota
            ############

            # Get telephoneNumber.
            telephoneNumber = data.get('telephoneNumber', [])
            nums = [str(num) for num in telephoneNumber if len(num) > 0]
            mod_attrs += [(ldap.MOD_REPLACE, 'telephoneNumber', nums)]

            # Get accountStatus.
            if 'accountStatus' in data.keys():
                accountStatus = 'active'
            else:
                accountStatus = 'disabled'
            mod_attrs += [(ldap.MOD_REPLACE, 'accountStatus', accountStatus)]

        elif self.profile_type == 'password':
            # Get password length from @domainAccountSetting.
            minPasswordLength = domainAccountSetting.get('minPasswordLength', settings.min_passwd_length)
            maxPasswordLength = domainAccountSetting.get('maxPasswordLength', settings.max_passwd_length)

            # Get new passwords from user input.
            self.newpw = str(data.get('newpw', None))
            self.confirmpw = str(data.get('confirmpw', None))

            result = iredutils.verify_new_password(
                newpw=self.newpw,
                confirmpw=self.confirmpw,
                min_passwd_length=minPasswordLength,
                max_passwd_length=maxPasswordLength,
            )
            if result[0] is True:
                if 'storePasswordInPlainText' in data and settings.STORE_PASSWORD_IN_PLAIN_TEXT:
                    self.passwd = iredutils.generate_password_hash(result[1], pwscheme='PLAIN')
                else:
                    self.passwd = iredutils.generate_password_hash(result[1])
                mod_attrs += [(ldap.MOD_REPLACE, 'userPassword', self.passwd)]
                mod_attrs += [(ldap.MOD_REPLACE, 'shadowLastChange', str(ldaputils.getDaysOfShadowLastChange()))]
            else:
                return result

        try:
            self.conn.modify_s(self.dn, mod_attrs)
            return (True, )
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))
