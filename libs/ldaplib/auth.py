# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import ldap


# Used for user auth.
def Auth(uri, dn, password, session=web.config.get('_session')):
    try:
        dn = web.safestr(dn.strip())
        password = password.strip()

        # Detect STARTTLS support.
        if uri.startswith('ldaps://'):
            starttls = True
        else:
            starttls = False

        # Set necessary option for STARTTLS.
        if starttls:
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

        conn = ldap.initialize(uri)

        # Set LDAP protocol version: LDAP v3.
        conn.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)

        if starttls:
            conn.set_option(ldap.OPT_X_TLS, ldap.OPT_X_TLS_DEMAND)

        try:
            # Verify username and password
            res = conn.bind_s(dn, password)

            if res:
                filter = '(&' + \
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
                    filter,
                    ['objectClass', 'domainGlobalAdmin', 'enabledService'])

                if not qr:
                    raise ldap.INVALID_CREDENTIALS

                entry = qr[0][1]
                if entry.get('domainGlobalAdmin', 'no')[0].lower() == 'yes':
                    session['domainGlobalAdmin'] = True

                if 'mailUser' in entry.get('objectClass'):
                    session['isMailUser'] = True

                    # Make sure user have 'domainGlobalAdmin=yes' for global
                    # admin or 'enabledService=domainadmin' for domain admin.
                    if not session.get('domainGlobalAdmin') \
                       or not 'domainadmin' in entry.get('enabledService', []):
                        return False

                conn.unbind_s()
                return True
            else:
                return False
        except ldap.INVALID_CREDENTIALS:
            return 'INVALID_CREDENTIALS'
        except ldap.SERVER_DOWN:
            return 'SERVER_DOWN'
        except ldap.LDAPError, e:
            if type(e.args) == dict and 'desc' in e.args.keys():
                return e.args['desc']
            else:
                return str(e)
    except Exception, e:
        return str(e)
