# Author: Zhang Huangbin <zhb@iredmail.org>

import ldap
import ldap.filter
import web
from libs import iredutils
from libs.ldaplib import core, attrs, ldaputils, iredldif, deltree, connUtils, decorators

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
        lang = self.conn.search_s(
            dn,
            ldap.SCOPE_BASE,
            attrlist=['preferredLanguage'],
        )
        if 'preferredLanguage' in lang[0][1].keys():
            lang = lang[0][1]['preferredLanguage'][0]
        else:
            lang = web.ctx.lang
        return lang

    # List all admin accounts.
    @decorators.require_global_admin
    def listAccounts(self, attrs=attrs.ADMIN_SEARCH_ATTRS):
        try:
            result_admin = self.conn.search_s(
                self.domainadmin_dn,
                ldap.SCOPE_ONELEVEL,
                '(objectClass=mailAdmin)',
                attrs,
            )
            result_user = self.conn.search_s(
                self.basedn,
                ldap.SCOPE_SUBTREE,
                '(&(objectClass=mailUser)(accountStatus=active)(enabledService=domainadmin))',
                attrs,
            )
            return (True, result_admin + result_user)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    # Get admin profile.
    def profile(self, mail, attributes=attrs.ADMIN_ATTRS_ALL):
        self.mail = web.safestr(mail)
        self.dn = ldaputils.convert_keyword_to_dn(self.mail, accountType='admin')
        if self.dn[0] is False:
            return self.dn

        try:
            self.admin_profile = self.conn.search_s(
                self.dn,
                ldap.SCOPE_BASE,
                '(&(objectClass=mailAdmin)(mail=%s))' % self.mail,
                attributes,
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

        if not iredutils.is_email(self.mail):
            return (False, 'INVALID_MAIL')

        self.domainGlobalAdmin = web.safestr(data.get('domainGlobalAdmin', 'no'))
        if self.domainGlobalAdmin not in ['yes', 'no', ]:
            self.domainGlobalAdmin = 'no'

        self.preferredLanguage = web.safestr(data.get('preferredLanguage', 'en_US'))

        # Check password.
        self.newpw = web.safestr(data.get('newpw'))
        self.confirmpw = web.safestr(data.get('confirmpw'))

        result = iredutils.verify_new_password(self.newpw, self.confirmpw)
        if result[0] is True:
            self.passwd = iredutils.generate_password_hash(result[1])
        else:
            return result

        ldif = iredldif.ldif_mailadmin(mail=self.mail,
                                       passwd=self.passwd,
                                       cn=self.cn,
                                       preferredLanguage=self.preferredLanguage,
                                       domainGlobalAdmin=self.domainGlobalAdmin)

        self.dn = ldaputils.convert_keyword_to_dn(self.mail, accountType='admin')
        if self.dn[0] is False:
            return self.dn

        try:
            self.conn.add_s(self.dn, ldif)
            web.logger(msg="Create admin: %s." % (self.mail), event='create',)
            return (True,)
        except ldap.ALREADY_EXISTS:
            return (False, 'ALREADY_EXISTS')
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    # Update admin profile.
    def update(self, profile_type, mail, data):
        self.profile_type = web.safestr(profile_type)
        self.mail = web.safestr(mail)
        self.username, self.domain = self.mail.split('@', 1)

        if session.get('domainGlobalAdmin') is not True and session.get('username') != self.mail:
            # Don't allow to view/update other admins' profile.
            return (False, 'PERMISSION_DENIED')

        self.dn = ldaputils.convert_keyword_to_dn(self.mail, accountType='admin')
        if self.dn[0] is False:
            return self.dn

        mod_attrs = []
        if self.profile_type == 'general':
            # Get preferredLanguage.
            lang = web.safestr(data.get('preferredLanguage', 'en_US'))
            mod_attrs += [(ldap.MOD_REPLACE, 'preferredLanguage', lang)]

            # Get cn.
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

            # Get accountStatus.
            if 'accountStatus' in data.keys():
                accountStatus = 'active'
            else:
                accountStatus = 'disabled'

            mod_attrs += [(ldap.MOD_REPLACE, 'accountStatus', accountStatus)]

            try:
                # Modify profiles.
                self.conn.modify_s(self.dn, mod_attrs)
                if session.get('username') == self.mail and \
                   session.get('lang', 'en_US') != lang:
                    session['lang'] = lang
            except ldap.LDAPError, e:
                return (False, ldaputils.getExceptionDesc(e))

        elif self.profile_type == 'password':
            self.cur_passwd = data.get('oldpw', None)
            self.newpw = web.safestr(data.get('newpw'))
            self.confirmpw = web.safestr(data.get('confirmpw'))

            result = iredutils.verify_new_password(self.newpw, self.confirmpw)
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

        return (True,)

    @decorators.require_global_admin
    def delete(self, mails):
        if mails is None or len(mails) == 0:
            return (False, 'NO_ACCOUNT_SELECTED')

        result = {}

        for mail in mails:
            self.mail = web.safestr(mail)
            dn = ldaputils.convert_keyword_to_dn(self.mail, accountType='admin')
            if dn[0] is False:
                return dn

            try:
                deltree.DelTree(self.conn, dn, ldap.SCOPE_SUBTREE)
                web.logger(msg="Delete admin: %s." % (self.mail,), event='delete',)
            except ldap.NO_SUCH_OBJECT:
                # This is a mail user admin
                dn = ldaputils.convert_keyword_to_dn(self.mail, accountType='user')
                try:
                    connutils = connUtils.Utils()
                    # Delete enabledService=domainadmin
                    connutils.addOrDelAttrValue(dn=dn,
                                                attr='enabledService',
                                                value='domainadmin',
                                                action='delete')

                    # Delete domainGlobalAdmin=yes
                    connutils.addOrDelAttrValue(dn=dn,
                                                attr='domainGlobalAdmin',
                                                value='yes',
                                                action='delete')
                    web.logger(msg="Delete admin: %s." % (self.mail), event='delete')
                except Exception, e:
                    result[self.mail] = str(e)
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
            if not iredutils.is_email(self.mail):
                continue

            self.domain = self.mail.split('@')[-1]
            self.dn = ldaputils.convert_keyword_to_dn(self.mail, accountType='admin')
            if self.dn[0] is False:
                return self.dn

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

    def getNumberOfManagedAccounts(self, admin=None, accountType='domain', domains=[],):
        if admin is None:
            admin = session.get('username')
        else:
            admin = str(admin)

        if not iredutils.is_email(admin):
            return 0

        domains = []
        if len(domains) > 0:
            domains = [str(d).lower() for d in domains if iredutils.is_domain(d)]
        else:
            connutils = connUtils.Utils()
            qr = connutils.getManagedDomains(mail=admin, attrs=['domainName'], listedOnly=True)
            if qr[0] is True:
                domains = qr[1]

        if accountType == 'domain':
            try:
                return len(domains)
            except Exception:
                pass

        return 0
