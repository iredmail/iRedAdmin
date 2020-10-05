#!/usr/bin/env python3
# Author: Zhang Huangbin <zhb@iredmail.org>
# Purpose: Update user password.
# Usage:
#   python reset_user_password.py <email> <new_password>


def usage():
    print("""Usage: Run this script with user email address and new plain password:

        # python3 reset_user_password.py user@domain.com 123456
    """)


import os
import sys
import web

os.environ['LC_ALL'] = 'C'

rootdir = os.path.abspath(os.path.dirname(__file__)) + '/../'
sys.path.insert(0, rootdir)

import settings
from tools.ira_tool_lib import debug, get_db_conn
from libs.iredutils import is_email
from libs.iredpwd import generate_password_hash

backend = settings.backend
web.config.debug = debug

# Check arguments
if len(sys.argv) == 3:
    email = sys.argv[1]
    pw = sys.argv[2]

    if not is_email(email):
        usage()
        sys.exit()
else:
    usage()
    sys.exit()

pw_hash = generate_password_hash(pw)
if backend == 'ldap':
    from libs.ldaplib.core import LDAPWrap
    from libs.ldaplib.ldaputils import rdn_value_to_user_dn, mod_replace
    _wrap = LDAPWrap()
    conn = _wrap.conn

    dn = rdn_value_to_user_dn(email)
    mod_attrs = mod_replace('userPassword', pw_hash)
    try:
        conn.modify_s(dn, mod_attrs)
        print("[{}] Password has been reset.".format(email))
    except Exception as e:
        print("<<< ERROR >>> {}".format(repr(e)))
elif backend in ['mysql', 'pgsql']:
    conn = get_db_conn('vmail')
    try:
        conn.update('mailbox',
                    password=pw_hash,
                    where="username='{}'".format(email))
        print("[{}] Password has been reset.".format(email))
    except Exception as e:
        print("<<< ERROR >>> {}".format(repr(e)))
