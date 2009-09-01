#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import sys
import ldap, ldap.filter
import web
from libs import iredutils
from libs.ldaplib import core, attrs, ldaputils, deltree

cfg = web.iredconfig
session = web.config.get('_session')
LDAPDecorators = core.LDAPDecorators()

class User(core.LDAPWrap):
    def __del__(self):
        pass

    # List all users under one domain.
    @LDAPDecorators.check_domain_access
    def list(self, domain):
        self.domain = domain
        self.domainDN = ldaputils.convDomainToDN(self.domain)

        # Check whether user is admin of domain.
        if self.check_domain_access(self.domainDN, session.get('username')):
            # Search users under domain.
            try:
                self.users = self.conn.search_s(
                        'ou=Users,' + self.domainDN,
                        ldap.SCOPE_SUBTREE,
                        '(objectClass=mailUser)',
                        attrs.USER_SEARCH_ATTRS,
                        )

                self.updateAttrSingleValue(self.domainDN, 'domainCurrentUserNumber', len(self.users))

                return self.users
            except ldap.NO_SUCH_OBJECT:
                self.conn.add_s(
                        'ou=Users,'+ self.domainDN,
                        iredldif.ldif_group('Users'),
                        )
                return []
            except ldap.SIZELIMIT_EXCEEDED:
                return 'SIZELIMIT_EXCEEDED'
            except Exception, e:
                return str(e)
        else:
            return False

    # Get values of user dn.
    @LDAPDecorators.check_domain_access
    def profile(self, mail):
        self.dn = ldaputils.convEmailToUserDN(mail)
        self.user_profile = self.conn.search_s(
                str(self.dn),
                ldap.SCOPE_BASE,
                '(objectClass=mailUser)',
                attrs.USER_ATTRS_ALL,
                )

        return self.user_profile

    def add(self, dn, ldif):
        try:
            self.conn.add_s(ldap.filter.escape_filter_chars(dn), ldif,)
            return True
        except ldap.ALREADY_EXISTS:
            return 'ALREADY_EXISTS'
        except Exception, e:
            return str(e)

    @LDAPDecorators.check_global_admin
    def delete(self, mails=[]):
        if mails is None or len(mails) == 0: return False

        msg = {}
        for mail in mails:
            dn = ldaputils.convEmailToUserDN(mail)

            try:
                deltree.DelTree( self.conn, dn, ldap.SCOPE_SUBTREE )
            except ldap.LDAPError, e:
                msg[mail] = str(e)

        if msg == {}: return True
        else: return False

    @LDAPDecorators.check_domain_access
    def update(self, profile_type, mail, data):
        self.profile_type = web.safestr(profile_type)
        self.mail = web.safestr(mail)
        self.domain = self.mail.split('@', 1)[1]

        mod_attrs = []
        if self.profile_type == 'general':
            # Get cn.
            cn = data.get('cn', None)

            if cn is not None:
                mod_attrs = [ ( ldap.MOD_REPLACE, 'cn', cn.encode('utf-8') ) ]
            else:
                # Delete attribute.
                mod_attrs = [ ( ldap.MOD_DELETE, 'cn', None) ]

            # Get mail address.

            # Get mailQuota.
            mailQuota = web.safestr(data.get('mailQuota', None))
            if mailQuota == '':
                # Don't touch it, keep old quota value.
                pass
            else:
                mod_attrs = [ ( ldap.MOD_REPLACE, 'mailQuota', str(int(mailQuota) * 1024 * 1024) ) ]

            # Get accountStatus.
            accountStatus = web.safestr(data.get('accountStatus', 'active'))
            if accountStatus not in attrs.VALUES_ACCOUNT_STATUS:
                accountStatus = 'active'

            mod_attrs += [ (ldap.MOD_REPLACE, 'accountStatus', accountStatus) ]
        elif self.profile_type == 'password':
            # Get new passwords from user input.
            self.newpw = str(data.get('newpw', None))
            self.confirmpw = str(data.get('confirmpw', None))
             
            self.result = iredutils.getNewPassword(newpw=self.newpw, confirmpw=self.confirmpw,)
            if self.result[0] is True:
                self.passwd = ldaputils.generatePasswd(self.result[1], pwscheme=cfg.general.get('default_pw_scheme', 'SSHA'))
                mod_attrs += [ (ldap.MOD_REPLACE, 'userPassword', self.passwd) ]
            else:
                return self.result

        try:
            dn = ldaputils.convEmailToUserDN(self.mail)
            self.conn.modify_s(dn, mod_attrs)
            return True
        except Exception, e:
            return (False, str(e))
