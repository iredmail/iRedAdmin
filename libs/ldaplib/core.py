#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import os, sys, time
import web
import ldap
from libs.ldaplib import attrs, iredutils

cfg = web.iredconfig
session = web.config.get('_session')

class LDAPWrap:
    def __init__(self, app=web.app, session=session, **settings):
        # Get LDAP settings.
        self.basedn = cfg.ldap.get('basedn')
        self.domainadmin_dn = cfg.ldap.get('domainadmin_dn')
        self.bind_dn = cfg.ldap.get('bind_dn')
        self.bind_pw = cfg.ldap.get('bind_pw')

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
        ldap.set_option(ldap.OPT_SIZELIMIT, 100)
        self.conn.set_option(ldap.OPT_SIZELIMIT, 100)

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
        self.conn.bind_s(self.bind_dn, self.bind_pw)

        '''
        # Get default language.
        lang = self.conn.search_s(
                session.get('userdn'),
                ldap.SCOPE_BASE,
                '(objectClass=mailAdmin)',
                ['preferredLanguage'],
                )
        if lang[0][1].has_key('preferredLanguage'):
            session['lang'] = lang[0][1]
        else:
            self.conn.modify_s(
                    session.get('userdn'),
                    [(ldap.MOD_ADD, 'preferredLanguage', cfg.general.get('lang'))],
                    )

            session['lang'] = cfg.general.get('lang')
        '''

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
        domainName = iredutils.extractValueFromDN(domainDN, 'domainName')
        if domainName is None: return False

        admin = web.safestr(admin)

        # Check domain exist.
        if self.check_dn_exist(domainDN):
            if session.get('domainGlobalAdmin') == 'yes':
                #return True
                #"""
                try:
                    self.access = self.conn.search_s(
                            iredutils.convEmailToAdminDN(admin),
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

    def change_passwd(self, dn, cur_passwd, new_passwd, new_passwd_confirm):
        # Username should be dn.
        if cur_passwd == '':
            return 'EMPTY_CUR_PW'
        elif new_passwd == '' or new_passwd_confirm == '':
            return 'EMPTY_NEW_PW'
        elif new_passwd != new_passwd_confirm:
            # Verify new password.
            return 'NEW_PW_NOT_SAME'
        else:
            try:
                # Reference: RFC3062 - LDAP Password Modify Extended Operation
                self.conn.passwd_s(dn, cur_passwd, new_passwd)
                return True
            except ldap.UNWILLING_TO_PERFORM, e:
                if web.safestr(e.args[0].get('info')) == 'unwilling to verify old password':
                    return 'BAD_OLD_PASSWD'
                else:
                    return 'UNWILLING_TO_PERFORM'
            except ldap.LDAPError, e:
                return str(e.args[0].get('info'))

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
