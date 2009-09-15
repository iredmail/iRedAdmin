#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import sys
import ldap, ldap.filter
import web
from libs import iredutils
from libs.ldaplib import core, domain, attrs, ldaputils, iredldif, deltree

cfg = web.iredconfig
session = web.config.get('_session')
LDAPDecorators = core.LDAPDecorators()

domainLib = domain.Domain()

class User(core.LDAPWrap):
    def __del__(self):
        pass

    # List all users under one domain.
    @LDAPDecorators.check_domain_access
    def list(self, domain):
        self.domain = domain
        self.domainDN = ldaputils.convDomainToDN(self.domain)

        try:
            self.users = self.conn.search_s(
                    'ou=Users,' + self.domainDN,
                    ldap.SCOPE_SUBTREE,
                    '(objectClass=mailUser)',
                    attrs.USER_SEARCH_ATTRS,
                    )
            self.updateAttrSingleValue(self.domainDN, 'domainCurrentUserNumber', len(self.users))

            return (True, self.users)
        except ldap.NO_SUCH_OBJECT:
            #self.conn.add_s(
            #        'ou=Users,'+ self.domainDN,
            #        iredldif.ldif_group('Users'),
            #        )
            return (False, 'NO_SUCH_OBJECT')
        except ldap.SIZELIMIT_EXCEEDED:
            return (False, 'SIZELIMIT_EXCEEDED')
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    # Get values of user dn.
    @LDAPDecorators.check_domain_access
    def profile(self, mail):
        self.mail = web.safestr(mail)
        self.dn = ldaputils.convEmailToUserDN(self.mail)
        try:
            self.user_profile = self.conn.search_s(
                    self.dn,
                    ldap.SCOPE_BASE,
                    '(objectClass=mailUser)',
                    attrs.USER_ATTRS_ALL,
                    )
            return (True, self.user_profile)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))


    @LDAPDecorators.check_domain_access
    def add(self, domain, data):
        # Get domain name, username, cn.
        self.domain = web.safestr(data.get('domainName')).lower()
        self.username = web.safestr(data.get('username')).lower()

        if self.domain == '' or self.username == '':
            return (False, 'MISSING_DOMAIN_OR_USERNAME')

        # Check password.
        self.newpw = web.safestr(data.get('newpw'))
        self.confirmpw = web.safestr(data.get('confirmpw'))

        result = iredutils.getNewPassword(self.newpw, self.confirmpw)
        if result[0] is True:
            self.passwd = ldaputils.generatePasswd(result[1], pwscheme=cfg.general.get('default_pw_scheme', 'SSHA'))
        else:
            return result

        self.cn = data.get('cn')
        self.quota = data.get('mailQuota', domainLib.getDomainDefaultUserQuota(self.domain))

        ldif = iredldif.ldif_mailuser(
                domain=self.domain,
                username=self.username,
                cn=self.cn,
                passwd=self.passwd,
                quota=self.quota,
                )

        self.dn = ldaputils.convEmailToUserDN(self.username + '@' + self.domain)

        try:
            self.conn.add_s(ldap.filter.escape_filter_chars(self.dn), ldif,)
            return (True, 'SUCCESS')
        except ldap.ALREADY_EXISTS:
            return (False, 'ALREADY_EXISTS')
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    @LDAPDecorators.check_domain_access
    def delete(self, domain, mails=[]):
        if mails is None or len(mails) == 0: return False

        result = {}
        for mail in mails:
            self.mail = web.safestr(mail)
            dn = ldaputils.convEmailToUserDN(self.mail)

            try:
                deltree.DelTree( self.conn, dn, ldap.SCOPE_SUBTREE )
            except ldap.LDAPError, e:
                result[self.mail] = str(e)

        if result == {}:
            return (True, 'SUCCESS')
        else:
            return (False, result)

    @LDAPDecorators.check_domain_access
    def update(self, profile_type, mail, data):
        self.profile_type = web.safestr(profile_type)
        self.mail = web.safestr(mail)
        self.domain = self.mail.split('@', 1)[1]

        mod_attrs = []
        if self.profile_type == 'general':
            # Get cn.
            cn = data.get('cn', None)
            mod_attrs += ldaputils.getSingleModAttr(attr='cn', value=cn, default=self.mail.split('@')[0])

            # Get mail address.

            # Get mailQuota.
            mailQuota = web.safestr(data.get('mailQuota', None))
            if mailQuota == '':
                # Don't touch it, keep old quota value.
                pass
            else:
                mod_attrs += [ ( ldap.MOD_REPLACE, 'mailQuota', str(int(mailQuota) * 1024 * 1024) ) ]

            # Get telephoneNumber.
            employeeNumber = data.get('employeeNumber', 'None')
            mod_attrs += ldaputils.getSingleModAttr(attr='employeeNumber', value=employeeNumber, default='None')

            telephoneNumber = data.get('telephoneNumber', [])
            if telephoneNumber != [] and telephoneNumber != [u''] and telephoneNumber != []:
                mod_attrs += [ (ldap.MOD_REPLACE, 'telephoneNumber', None) ]
                for i in telephoneNumber:
                    mod_attrs += [ ( ldap.MOD_REPLACE, 'telephoneNumber', web.safestr(i) ) ]

            # Get accountStatus.
            accountStatus = web.safestr(data.get('accountStatus', 'active'))
            if accountStatus not in attrs.VALUES_ACCOUNT_STATUS:
                accountStatus = 'active'

            mod_attrs += [ (ldap.MOD_REPLACE, 'accountStatus', accountStatus) ]
        elif self.profile_type == 'password':
            # Get new passwords from user input.
            self.newpw = str(data.get('newpw', None))
            self.confirmpw = str(data.get('confirmpw', None))
             
            result = iredutils.getNewPassword(newpw=self.newpw, confirmpw=self.confirmpw,)
            if result[0] is True:
                self.passwd = ldaputils.generatePasswd(result[1], pwscheme=cfg.general.get('default_pw_scheme', 'SSHA'))
                mod_attrs += [ (ldap.MOD_REPLACE, 'userPassword', self.passwd) ]
            else:
                return result

        try:
            dn = ldaputils.convEmailToUserDN(self.mail)
            self.conn.modify_s(dn, mod_attrs)
            return (True, 'SUCCESS')
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))
