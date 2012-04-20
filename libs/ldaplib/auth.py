# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import ldap
import ldap.filter


# Used for user auth.
def Auth(uri, dn, password, session=web.config.get('_session')):
    try:
        dn = ldap.filter.escape_filter_chars(web.safestr(dn.strip()))
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
            res = conn.bind_s(dn, password)

            if res:
                # Check whether this user is a site wide global admin.
                global_admin_result = conn.search_s(
                    dn,
                    ldap.SCOPE_BASE,
                    "(&(objectClass=mailAdmin)(accountStatus=active))",
                    ['domainGlobalAdmin']
                )
                if not global_admin_result:
                    raise ldap.INVALID_CREDENTIALS

                result = global_admin_result[0][1]
                if result.get('domainGlobalAdmin', 'no')[0].lower() == 'yes':
                    session['domainGlobalAdmin'] = True
                else:
                    session['domainGlobalAdmin'] = False

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
