# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import ldap
from libs import settings
from libs.ldaplib import attrs

cfg = web.iredconfig
session = web.config.get('_session')


class LDAPWrap:
    def __init__(self, app=web.app, session=session,):
        # Get LDAP settings.
        self.basedn = cfg.ldap.get('basedn')
        self.domainadmin_dn = cfg.ldap.get('domainadmin_dn')

        # Initialize LDAP connection.
        try:
            # Get LDAP URI.
            uri = cfg.ldap.get('uri', 'ldap://127.0.0.1')

            # Detect STARTTLS support.
            if uri.startswith('ldaps://'):
                starttls = True
            else:
                starttls = False

            # Set necessary option for STARTTLS.
            if starttls:
                ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

            # Initialize connection.
            self.conn = ldap.initialize(uri, trace_level=settings.LDAP_CONN_TRACE_LEVEL,)

            # Set LDAP protocol version: LDAP v3.
            self.conn.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)

            if starttls:
                self.conn.set_option(ldap.OPT_X_TLS, ldap.OPT_X_TLS_DEMAND)

        except:
            return False

        # synchronous bind.
        self.conn.bind_s(cfg.ldap.get('bind_dn'), cfg.ldap.get('bind_pw'))

    def __del__(self):
        try:
            self.conn.unbind()
        except:
            pass

    # List all domains.
    def getAllDomains(self, attrs=attrs.DOMAIN_SEARCH_ATTRS, filter=None,):
        admin = session.get('username')
        if admin is None:
            return (False, 'INVALID_USERNAME')

        # Check whether admin is a site wide admin.
        if filter is None:
            if session.get('domainGlobalAdmin') is True:
                self.filter = '(objectClass=mailDomain)'
            else:
                self.filter = '(&(objectClass=mailDomain)(domainAdmin=%s))' % (admin)
        else:
            if session.get('domainGlobalAdmin') is True:
                self.filter = filter
            else:
                self.filter = '(&' + filter + ')'

        # List all domains under control.
        try:
            self.domains = self.conn.search_s(
                self.basedn,
                ldap.SCOPE_ONELEVEL,
                self.filter,
                attrs,
            )
            return (True, self.domains)
        except Exception, e:
            return (False, str(e))
