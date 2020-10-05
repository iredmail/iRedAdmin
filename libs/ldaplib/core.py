# Author: Zhang Huangbin <zhb@iredmail.org>

import ldap
import settings
from libs.logger import logger


class LDAPWrap:
    def __init__(self):
        # Initialize LDAP connection.
        self.conn = None

        uri = settings.ldap_uri

        # Detect STARTTLS support.
        starttls = False
        if uri.startswith('ldaps://'):
            starttls = True

            # Rebuild uri, use ldap:// + STARTTLS (with normal port 389)
            # instead of ldaps:// (port 636) for secure connection.
            uri = uri.replace('ldaps://', 'ldap://')

            # Don't check CA cert
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

        self.conn = ldap.initialize(uri=uri)

        # Set LDAP protocol version: LDAP v3.
        self.conn.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)

        if starttls:
            self.conn.start_tls_s()

        try:
            # bind as vmailadmin
            self.conn.bind_s(settings.ldap_bind_dn, settings.ldap_bind_password)
        except Exception as e:
            logger.error('VMAILADMIN_INVALID_CREDENTIALS. Detail: %s' % repr(e))

    def __del__(self):
        try:
            if self.conn:
                self.conn.unbind()
        except:
            pass
