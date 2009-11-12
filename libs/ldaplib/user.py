#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

#---------------------------------------------------------------------
# This file is part of iRedAdmin-OSE, which is official web-based admin
# panel (Open Source Edition) for iRedMail.
#
# iRedMail is an open source mail server solution for Red Hat(R)
# Enterprise Linux, CentOS, Debian and Ubuntu.
#
# iRedAdmin-OSE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# iRedAdmin-OSE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with iRedAdmin-OSE.  If not, see <http://www.gnu.org/licenses/>.
#---------------------------------------------------------------------

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
    @LDAPDecorators.require_domain_access
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
            return (False, 'msg=NO_SUCH_OBJECT')
        except ldap.SIZELIMIT_EXCEEDED:
            return (False, 'msg=SIZELIMIT_EXCEEDED')
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    # Get values of user dn.
    @LDAPDecorators.require_domain_access
    def profile(self, domain, mail):
        self.mail = web.safestr(mail)
        self.dn = ldaputils.convEmailToUserDN(self.mail)
        try:
            self.user_profile = self.conn.search_s(
                    self.dn,
                    ldap.SCOPE_BASE,
                    '(&(objectClass=mailUser)(mail=%s))' % self.mail,
                    attrs.USER_ATTRS_ALL,
                    )
            return (True, self.user_profile)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))


    @LDAPDecorators.require_domain_access
    def add(self, domain, data):
        # Get domain name, username, cn.
        self.domain = web.safestr(data.get('domainName')).lower()
        self.username = web.safestr(data.get('username')).lower()

        if self.domain == '' or self.username == '':
            return (False, 'msg=MISSING_DOMAIN_OR_USERNAME')

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
            return (True,)
        except ldap.ALREADY_EXISTS:
            return (False, 'ALREADY_EXISTS')
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    @LDAPDecorators.require_domain_access
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
            return (True,)
        else:
            return (False, ldaputils.getExceptionDesc(result))

    @LDAPDecorators.require_domain_access
    def enableOrDisableAccount(self, domain, mails, value, attr='accountStatus',):
        if mails is None or len(mails) == 0: return (False, 'msg=NO_ACCOUNT_SELECTED')

        result = {}
        for mail in mails:
            self.mail = web.safestr(mail)
            self.dn = ldaputils.convEmailToUserDN(self.mail)

            try:
                self.updateAttrSingleValue(
                        dn=self.dn,
                        attr=web.safestr(attr),
                        value=web.safestr(value),
                        )
            except ldap.LDAPError, e:
                result[self.mail] = str(e)

        if result == {}:
            return (True,)
        else:
            return (False, ldaputils.getExceptionDesc(result))

    @LDAPDecorators.require_domain_access
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
            employeeNumber = data.get('employeeNumber', None)
            mod_attrs += ldaputils.getSingleModAttr(attr='employeeNumber', value=employeeNumber, default=None)

            telephoneNumber = data.get('telephoneNumber', [])
            if telephoneNumber != [] and telephoneNumber != [u''] and telephoneNumber != []:
                mod_attrs += [ (ldap.MOD_REPLACE, 'telephoneNumber', None) ]
                for i in telephoneNumber:
                    mod_attrs += [ ( ldap.MOD_REPLACE, 'telephoneNumber', web.safestr(i) ) ]

            # Get accountStatus.
            if data.has_key('accountStatus'): accountStatus = 'active'
            else: accountStatus = 'disabled'

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
            return (True,)
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))
