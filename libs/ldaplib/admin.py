# Author: Zhang Huangbin <zhb@iredmail.org>

import sys
import ldap, ldap.filter
import web
from libs import iredutils
from libs.ldaplib import core, attrs, ldaputils, iredldif, deltree, connUtils, decorators

cfg = web.iredconfig
session = web.config.get('_session')


class Admin(core.LDAPWrap):
    def __del__(self):
        try:
            self.conn.unbind()
        except:
            pass

    # Get preferredLanguage.
    def getPreferredLanguage(self, dn):
        dn = ldap.filter.escape_filter_chars(dn)
        self.lang = self.conn.search_s(
            dn,
            ldap.SCOPE_BASE,
            attrlist=['preferredLanguage'],
        )
        if 'preferredLanguage' in self.lang[0][1].keys():
            lang = self.lang[0][1]['preferredLanguage'][0]
        else:
            lang = web.ctx.lang
        return lang

    # Get domains under control.
    def getManagedDomains(self, mail, attrs=attrs.ADMIN_ATTRS_ALL):
        self.mail = web.safestr(mail)
        if not iredutils.isEmail(self.mail):
            return (False, 'INCORRECT_USERNAME')

        # Pre-defined filter.
        filter = '(&(objectClass=mailDomain)(domainAdmin=%s))' % self.mail

        # Check admin type: global/normal admin.
        try:
            profile = self.profile(self.mail)
            if profile[1][0][1].get('domainGlobalAdmin', ['no'])[0] == 'yes':
                filter = '(objectClass=mailDomain)'
        except:
            pass

        try:
            self.managedDomains = self.conn.search_s(
                self.basedn,
                ldap.SCOPE_ONELEVEL,
                filter,
                attrs,
            )
            return (True, self.managedDomains)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    # List all admin accounts.
    @decorators.require_global_admin
    def listAccounts(self, attrs=attrs.ADMIN_SEARCH_ATTRS):
        filter = "(objectClass=mailAdmin)"
        try:
            result = self.conn.search_s(
                self.domainadmin_dn,
                ldap.SCOPE_ONELEVEL,
                filter,
                attrs,
            )
            return (True, result)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    # Get admin profile.
    def profile(self, mail):
        self.mail = web.safestr(mail)
        self.dn = ldaputils.convKeywordToDN(self.mail, accountType='admin')
        try:
            self.admin_profile = self.conn.search_s(
                self.dn,
                ldap.SCOPE_BASE,
                '(&(objectClass=mailAdmin)(mail=%s))' % self.mail,
                attrs.ADMIN_ATTRS_ALL,
            )
            return (True, self.admin_profile)
        except ldap.NO_SUCH_OBJECT:
            return (False, 'NO_SUCH_OBJECT')
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    # Add new admin.
    @decorators.require_global_admin
    def add(self, data):
        self.cn = data.get('cn')
        self.mail = web.safestr(data.get('mail')).strip().lower()

        if not iredutils.isEmail(self.mail):
            return (False, 'INVALID_MAIL')

        self.domainGlobalAdmin = web.safestr(data.get('domainGlobalAdmin', 'no'))
        if self.domainGlobalAdmin not in ['yes', 'no',]:
            self.domainGlobalAdmin = 'no'

        self.preferredLanguage = web.safestr(data.get('preferredLanguage', 'en_US'))

        # Check password.
        self.newpw = web.safestr(data.get('newpw'))
        self.confirmpw = web.safestr(data.get('confirmpw'))

        result = iredutils.verifyNewPasswords(self.newpw, self.confirmpw)
        if result[0] is True:
            self.passwd = ldaputils.generatePasswd(result[1])
        else:
            return result

        ldif = iredldif.ldif_mailadmin(
                mail=self.mail,
                passwd=self.passwd,
                cn=self.cn,
                preferredLanguage=self.preferredLanguage,
                domainGlobalAdmin=self.domainGlobalAdmin,
                )

        self.dn = ldaputils.convKeywordToDN(self.mail, accountType='admin')

        try:
            self.conn.add_s(self.dn, ldif)
            web.logger(msg="Create admin: %s." % (self.mail), event='create',)
            return (True,)
        except ldap.ALREADY_EXISTS:
            return (False, 'ALREADY_EXISTS')
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    # Update admin profile.
    # data: must be a webpy storage object.
    def update(self, profile_type, mail, data):
        self.profile_type = web.safestr(profile_type)
        self.mail = web.safestr(mail)

        if session.get('domainGlobalAdmin') is not True and session.get('username') != self.mail:
            # Don't allow to view/update other admins' profile.
            return (False, 'PERMISSION_DENIED')

        self.dn = ldaputils.convKeywordToDN(self.mail, accountType='admin')

        mod_attrs = []
        if self.profile_type == 'general':
            # Get preferredLanguage.
            self.lang = web.safestr(data.get('preferredLanguage', 'en_US'))
            mod_attrs += [(ldap.MOD_REPLACE, 'preferredLanguage', self.lang)]

            # Get cn.
            cn = data.get('cn', None)
            mod_attrs += ldaputils.getSingleModAttr(attr='cn', value=cn, default=self.mail.split('@')[0],)

            # Get accountStatus.
            if 'accountStatus' in data.keys():
                accountStatus = 'active'
            else:
                accountStatus = 'disabled'

            mod_attrs += [ (ldap.MOD_REPLACE, 'accountStatus', accountStatus) ]

            # Get domainGlobalAdmin.
            if 'domainGlobalAdmin' in data.keys():
                self.domainGlobalAdmin = 'yes'
            else:
                self.domainGlobalAdmin = 'no'
            mod_attrs += [(ldap.MOD_REPLACE, 'domainGlobalAdmin', self.domainGlobalAdmin)]

            try:
                # Modify profiles.
                self.conn.modify_s(self.dn, mod_attrs)
                if session.get('username') == self.mail:
                    session['lang'] = self.lang

                    if self.domainGlobalAdmin == 'no':
                        session['domainGlobalAdmin'] = False
            except ldap.LDAPError, e:
                return (False, ldaputils.getExceptionDesc(e))

            #########################
            # Managed domains
            #
            if session.get('domainGlobalAdmin') is not True:
                return (False, 'PERMISSION_DENIED')

            # Get domains under control.
            result = self.getManagedDomains(mail=self.mail, attrs=['domainName',])
            if result[0] is True:
                self.managedDomains = []
                for d in result[1]:
                    if 'domainName' in d[1].keys():
                        self.managedDomains += d[1].get('domainName')
            else:
                return result

            # Get domains from web form.
            self.newmd = [web.safestr(v) for v in data.get('domainName', []) if iredutils.isDomain(v)]

            # Compare two lists, get domain list which need to remove or add domain admins.
            self.domainsRemoveAdmins = [str(v)
                                        for v in self.managedDomains
                                        if v not in self.newmd and iredutils.isDomain(v)
                                       ]
            self.domainsAddAdmins = [str(v)
                                     for v in self.newmd
                                     if v not in self.managedDomains and iredutils.isDomain(v)
                                    ]

            connutils = connUtils.Utils()
            for i in self.domainsRemoveAdmins:
                result = connutils.addOrDelAttrValue(
                        dn=ldaputils.convKeywordToDN(i, accountType='domain'),
                        attr='domainAdmin',
                        value=self.mail,
                        action='delete',
                        )
                if result[0] is False:
                    return result

            for i in self.domainsAddAdmins:
                result = connutils.addOrDelAttrValue(
                        dn=ldaputils.convKeywordToDN(i, accountType='domain'),
                        attr='domainAdmin',
                        value=self.mail,
                        action='add',
                        )
                if result[0] is False:
                    return result
            return (True,)
        elif self.profile_type == 'password':
            self.cur_passwd = data.get('oldpw', None)
            self.newpw = data.get('newpw')
            self.confirmpw = data.get('confirmpw')

            result = iredutils.verifyNewPasswords(self.newpw, self.confirmpw)
            if result[0] is True:
                self.passwd = result[1]
            else:
                return result

            # Change password.
            if self.cur_passwd is None and session.get('domainGlobalAdmin') is True:
                # Reset password without verify old password.
                self.cur_passwd = None
            else:
                self.cur_passwd = str(self.cur_passwd)

            connutils = connUtils.Utils()
            result = connutils.changePasswd(dn=self.dn, cur_passwd=self.cur_passwd, newpw=self.passwd,)
            if result[0] is True:
                return (True,)
            else:
                return result

    @decorators.require_global_admin
    def delete(self, mails):
        if mails is None or len(mails) == 0:
            return (False, 'NO_ACCOUNT_SELECTED')

        result = {}

        for mail in mails:
            self.mail = web.safestr(mail)
            dn = ldaputils.convKeywordToDN(self.mail, accountType='admin')

            try:
                deltree.DelTree( self.conn, dn, ldap.SCOPE_SUBTREE )
                web.logger(msg="Delete admin: %s." % (self.mail,), event='delete',)
            except ldap.LDAPError, e:
                result[self.mail] = str(e)

        if result == {}:
            return (True,)
        else:
            return (False, ldaputils.getExceptionDesc(result))

    @decorators.require_global_admin
    def enableOrDisableAccount(self, mails, action, attr='accountStatus',):
        if mails is None or len(mails) == 0:
            return (False, 'NO_ACCOUNT_SELECTED')

        result = {}
        connutils = connUtils.Utils()
        for mail in mails:
            self.mail = web.safestr(mail).strip().lower()
            if not iredutils.isEmail(self.mail):
                continue

            self.domain = self.mail.split('@')[-1]
            self.dn = ldaputils.convKeywordToDN(self.mail, accountType='admin')

            try:
                connutils.enableOrDisableAccount(
                    domain=self.domain,
                    account=self.mail,
                    dn=self.dn,
                    action=web.safestr(action).strip().lower(),
                    accountTypeInLogger='admin',
                )
            except ldap.LDAPError, e:
                result[self.mail] = str(e)

        if result == {}:
            return (True,)
        else:
            return (False, ldaputils.getExceptionDesc(result))
