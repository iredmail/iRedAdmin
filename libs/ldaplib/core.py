#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import os, sys, time
import web
import ldap, ldap.filter
from libs import iredutils
from libs.ldaplib import attrs, ldaputils

cfg = web.iredconfig
session = web.config.get('_session')

class LDAPWrap:
    def __init__(self, app=web.app, session=session, **settings):
        # Get LDAP settings.
        self.basedn = cfg.ldap.get('basedn')
        self.domainadmin_dn = cfg.ldap.get('domainadmin_dn')

        # Initialize LDAP connection.
        try:
            self.conn = ldap.initialize(cfg.ldap.get('uri', 'ldap://127.0.0.1'))

            #self.conn.protocol_version = ldap.VERSION3
            # Set LDAP protocol version.
            pro_version = int(cfg.ldap.get('protocol_version', 0))
            if pro_version:
                self.conn.set_option(ldap.OPT_PROTOCOL_VERSION, pro_version)
            else:
                self.conn.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)
        except Exception, e:
            return False

        # Set default size limit.
        #self.conn.set_option(ldap.OPT_SIZELIMIT, int(ldapconf.LDAP_SIZELIMIT))
        #ldap.set_option(ldap.OPT_SIZELIMIT, 100)
        #self.conn.set_option(ldap.OPT_SIZELIMIT, 100)

        # Set log level.
        #self.conn.set_option(ldap.OPT_DEBUG_LEVEL, int(ldapconf.LDAP_DEBUG_LEVEL))
        #ldap.set_option(ldap.OPT_DEBUG_LEVEL, int(ldapconf.LDAP_DEBUG_LEVEL))

        use_tls = eval(cfg.ldap.get('use_tls', '0'))
        if use_tls:
            try:
                self.conn.start_tls_s()
            except ldap.LDAPError, e:
                return e

        # synchronous bind.
        self.conn.bind_s(cfg.ldap.get('bind_dn'), cfg.ldap.get('bind_pw'))

    def __del__(self):
        self.conn.unbind()

    def check_dn_exist(self, dn):
        try:
            result = self.conn.search_s(
                    dn,
                    ldap.SCOPE_BASE,
                    '(objectClass=*)',
                    )
            return True
        except ldap.NO_SUCH_OBJECT:
            return False
        except:
            return False

    def check_global_admin(func):
        def proxyfunc(self, *args, **kw):
            if session.get('domainGlobalAdmin') == 'yes':
                return func(self, *args, **kw)
            else:
                return False
        return proxyfunc

    def check_domain_access(self, domainDN, admin):
        domainDN = web.safestr(domainDN)
        domainName = ldaputils.extractValueFromDN(domainDN, 'domainName')
        if domainName is None: return False

        admin = web.safestr(admin)

        # Check domain exist.
        if self.check_dn_exist(domainDN):
            if session.get('domainGlobalAdmin') == 'yes':
                #return True
                #"""
                try:
                    self.access = self.conn.search_s(
                            ldaputils.convEmailToAdminDN(admin),
                            ldap.SCOPE_BASE,
                            "(&(objectClass=mailAdmin)(domainGlobalAdmin=yes))",
                            )
                    if len(self.access) == 1:
                        return True
                    else:
                        return False
                except:
                    return False    # Not a domain global admin.
                #"""
            else:
                self.access = self.conn.search_s(
                        domainDN,
                        ldap.SCOPE_BASE,
                        "(&(domainName=%s)(domainAdmin=%s))" % (domainName, admin),
                        ['domainAdmin'],
                        )

                if len(self.access) == 1:
                    #else:
                    entry = self.access[0][1]
                    if entry.has_key('domainAdmin') and admin in entry.get('domainAdmin'):
                        return True
                    else:
                        return False
                else:
                    return False

    def init_passwd(self, dn, passwd):
        self.conn.passwd_s(dn, '', passwd)

    def change_passwd(self, dn, cur_passwd, newpw):
        dn = ldap.filter.escape_filter_chars(dn)
        try:
            # Reference: RFC3062 - LDAP Password Modify Extended Operation
            self.conn.passwd_s(dn, cur_passwd, newpw)
            return (True, 'SUCCESS')
        except ldap.UNWILLING_TO_PERFORM:
            return (False, 'INCORRECT_OLDPW')
        except Exception, e:
            return (False, ldaputils.getExceptionDesc(e))

    def check_domain_exist(self, domainName):
        self.result = self.conn.search_s(
                self.basedn,
                ldap.SCOPE_ONELEVEL,
                "(domainName=%s)" % (domainName),
                )

        if len(self.result) == 1:
            return True
        else:
            return False

    def updateAttrSingleValue(self, dn, attr, value):
        self.mod_attrs = [
                ( ldap.MOD_REPLACE, web.safestr(attr), web.safestr(value) )
                ]
        result = self.conn.modify_s(web.safestr(dn), self.mod_attrs)
        return result

    # List all domains.
    def get_all_domains(self, attrs=attrs.DOMAIN_SEARCH_ATTRS):
        admin = session.get('username', None)
        if admin is None: return False

        # Check whether admin is a site wide admin.
        if session.get('domainGlobalAdmin') == 'yes':
            filter = '(objectClass=mailDomain)'
        else:
            filter = '(&(objectClass=mailDomain)(domainAdmin=%s))' % (admin)

        # List all domains under control.
        try:
            self.domains = self.conn.search_s(
                    self.basedn,
                    ldap.SCOPE_ONELEVEL,
                    filter,
                    attrs,
                    )
            return self.domains
        except Exception, e:
            return str(e)

class LDAPDecorators(LDAPWrap):
    def __del__(self):
        pass

    def check_global_admin(self, func):
        def proxyfunc(self, *args, **kw):
            if session.get('domainGlobalAdmin') == 'yes':
                return func(self, *args, **kw)
            else:
                return False
        return proxyfunc

    def check_domain_access(self, func):
        def proxyfunc(self, *args, **kw):
            if kw.has_key('mail'):
                self.domain = web.safestr(kw['mail']).split('@', 1)[1]
            elif kw.has_key('domain'):
                self.domain = web.safestr(kw['domain'])

            if self.domain is None or self.domain == '': return False

            self.dn = ldaputils.convDomainToDN(self.domain)
            self.admin = session.get('username')

            # Check domain global admin.
            if session.get('domainGlobalAdmin') == 'yes':
                return func(self, *args, **kw)
            else:
                # Check whether is domain admin.
                result = self.conn.search_s(
                        self.dn,
                        ldap.SCOPE_BASE,
                        "(&(domainName=%s)(domainAdmin=%s))" % (self.domain, self.admin),
                        ['dn', 'domainAdmin'],
                        )
                if len(result) == 0:
                    web.seeother('/users' + '?msg=PERMISSION_DENIED&domain=' + self.domain)
                else:
                    return func(self, *args, **kw)
        return proxyfunc
