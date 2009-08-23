#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import sys
import ldap
import web
from libs.ldaplib import core, attrs, ldaputils

session = web.config.get('_session')

class Admin(core.LDAPWrap):
    def __del__(self):
        pass

    # Get preferredLanguage.
    def getPreferredLanguage(self, admin):
        dn = ldaputils.convEmailToAdminDN(web.safestr(admin))
        self.lang = self.conn.search_s(
                dn,
                ldap.SCOPE_BASE,
                attrlist=['preferredLanguage'],
                )
        if self.lang[0][1].has_key('preferredLanguage'):
            lang = self.lang[0][1]['preferredLanguage'][0]
        else:
            lang = session.get('lang')
        return lang

    # List all admin accounts.
    def list(self):
        filter = attrs.DOMAINADMIN_SEARCH_FILTER
        self.admins = self.conn.search_s(
                self.domainadmin_dn,
                ldap.SCOPE_ONELEVEL,
                filter,
                attrs.DOMAINADMIN_SEARCH_ATTRS,
                )

        return self.admins

    def add(self, admin, passwd, domainGlobalAdmin):
        # msg: {'admin': 'result'}
        msg = {}
        admin = str(admin)
        dn = "mail=" + admin + "," + self.domainadmin_dn
        ldif = iredldif.ldif_mailadmin(admin, passwd, domainGlobalAdmin)

        try:
            # Add object and initialize password.
            self.conn.add_s(dn, ldif)
            self.conn.passwd(dn, passwd, passwd)
            msg[admin] = 'SUCCESS'
        except ldap.ALREADY_EXISTS:
            msg[admin] = 'ALREADY_EXISTS'
        except ldap.LDAPError, e:
            msg[admin] = str(e)

        return msg

