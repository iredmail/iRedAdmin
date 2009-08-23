#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import web
import ldap, ldap.filter

cfg = web.iredconfig

# Used for user auth.
def Auth(dn, pw, session=web.config.get('_session')):
    try:
        conn = ldap.initialize(cfg.ldap.get('uri', 'ldap://127.0.0.1'))
        use_tls = eval(cfg.ldap.get('use_tls', 0))
        if use_tls:
            try:
                #self.conn.start_tls_s()
                conn.start_tls_s()
            except ldap.LDAPError, e:
                return e

        dn = ldap.filter.escape_filter_chars(web.safestr(dn.strip()))
        pw = pw.strip()

        try:
            res = conn.bind_s(dn, pw)

            if res:
                # Check whether this user is a site wide global admin.
                global_admin_result = conn.search_s(
                        dn,
                        ldap.SCOPE_BASE,
                        "(objectClass=*)",
                        ['domainGlobalAdmin']
                        )
                result = global_admin_result[0][1]
                if result.get('domainGlobalAdmin', 'no')[0].lower() == 'yes':
                    session['domainGlobalAdmin'] = 'yes'
                else:
                    pass

                return True
            else:
                return False
        except ldap.INVALID_CREDENTIALS:
            return 'INVALID_CREDENTIALS'
        except ldap.SERVER_DOWN:
            return 'SERVER_DOWN'
        except ldap.LDAPError, e:
            if type(e.args) == dict and e.args.has_key('desc'):
                return e.args['desc']
            else:
                return str(e)
    except Exception, e:
        return str(e)
