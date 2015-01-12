# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import ldap
import settings
from libs import iredutils
from libs.ldaplib import ldaputils


# Verify bind dn/pw or return LDAP connection object
# Return True if bind success, error message (string) if failed
def verify_bind_dn_pw(dn,
                      password,
                      uri=settings.ldap_uri,
                      close_connection=True):
    dn = web.safestr(dn.strip())
    password = password.strip()

    # Detect STARTTLS support.
    starttls = False
    if uri.startswith('ldaps://'):
        starttls = True

        # Rebuild uri, use ldap:// + STARTTLS (with normal port 389)
        # instead of ldaps:// (port 636) for secure connection.
        uri = uri.replace('ldaps://', 'ldap://')

        # Don't check CA cert
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

    conn = ldap.initialize(uri)

    # Set LDAP protocol version: LDAP v3.
    conn.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)

    if starttls:
        conn.start_tls_s()

    try:
        # bind as vmailadmin
        conn.bind_s(settings.ldap_bind_dn, settings.ldap_bind_password)
        qr = conn.search_s(dn,
                           ldap.SCOPE_BASE,
                           '(objectClass=*)',
                           ['userPassword'])
        if not qr:
            return (False, 'INVALID_CREDENTIALS')

        entries = qr[0][1]
        qr_password = entries.get('userPassword', [''])[0]
        if iredutils.verify_password_hash(qr_password, password):
            if close_connection:
                conn.unbind_s()
                return (True, )
            else:
                # Return connection
                return (True, conn)
        else:
            return (False, 'INVALID_CREDENTIALS')
    except Exception, e:
        return (False, ldaputils.getExceptionDesc(e))


# Used for user auth.
def Auth(uri, dn, password, session=web.config.get('_session')):
    qr = verify_bind_dn_pw(dn=dn,
                           password=password,
                           uri=uri,
                           close_connection=False)
    if qr[0]:
        conn = qr[1]
    else:
        return (False, qr[1])

    search_filter = '(&' + \
                    '(accountStatus=active)' + \
                    '(|' + \
                    '(objectClass=mailAdmin)' + \
                    '(&(objectClass=mailUser)(|(enabledService=domainadmin)(domainGlobalAdmin=yes)))' + \
                    ')' + \
                    ')'

    # Check whether this user is a site wide global admin.
    qr = conn.search_s(
        dn,
        ldap.SCOPE_BASE,
        search_filter,
        ['objectClass', 'domainGlobalAdmin', 'enabledService'])

    if not qr:
        # No such account.
        # WARN: Do not return message like 'INVALID USER', it will help
        #       cracker to perdict user existence.
        return (False, 'INVALID_CREDENTIALS')

    entry = qr[0][1]
    if entry.get('domainGlobalAdmin', 'no')[0].lower() == 'yes':
        session['domainGlobalAdmin'] = True

    if 'mailUser' in entry.get('objectClass'):
        # Make sure user have 'domainGlobalAdmin=yes' for global
        # admin or 'enabledService=domainadmin' for domain admin.
        if session.get('domainGlobalAdmin') \
           or 'domainadmin' in entry.get('enabledService', []):
            session['isMailUser'] = True
        else:
            return (False, 'INVALID_CREDENTIALS')

    conn.unbind_s()
    return (True, )
