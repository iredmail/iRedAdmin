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

import web
import ldap, ldap.filter

cfg = web.iredconfig
session = web.config.get('_session')

# Used for user auth.
def Auth(dn, pw, session=web.config.get('_session')):
    try:
        conn = ldap.initialize(cfg.ldap.get('uri', 'ldap://127.0.0.1'))

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

                # Update preferred language.
                try:
                    conn.modify_s(dn, [( ldap.MOD_REPLACE, 'preferredlanguage', web.safestr(session.get('lang', 'en_US')) )])
                except:
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
