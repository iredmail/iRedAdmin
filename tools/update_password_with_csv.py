#!/usr/bin/env python

# Author: Zhang Huangbin <zhb@iredmail.org>
# Purpose: Update user passwords from records in a CSV file.

def usage():
    print """Usage:

    - Store the email address and new password in a plain text file, e.g.
      'passwords.csv'. format is:

          <email> <new_password>

      Samples:

        user1@domain.com pF4mTq4jaRzDLlWl
        user2@domain.com SPhkTUlZs1TBxvmJ
        user3@domain.com 8deNR8IBLycRujDN

   - Run this script with this file:

        # python update_password_with_csv.py passwords.csv
    """

import os
import sys
import web

os.environ['LC_ALL'] = 'C'

rootdir = os.path.abspath(os.path.dirname(__file__)) + '/../'
sys.path.insert(0, rootdir)

import settings
from tools.ira_tool_lib import debug, logger, get_db_conn
from libs.iredutils import is_email
from libs.iredutils import generate_password_hash

backend = settings.backend
logger.info('Backend: %s' % backend)

web.config.debug = debug

logger.info('Parsing command line arguments.')

# File which stores email and quota.
text_file = ''

# The separator
column_separator = ' '

# List of (email, quota) tuples.
users = []

# Check arguments
if len(sys.argv) == 2:
    text_file = sys.argv[1]
    if not os.path.isfile(text_file):
        sys.exit('<<< ERROR>>> Not a regular file: %s' % text_file)

    # Get all (email, password) tuples.
    f = open(text_file, 'r')
    line_num = 0
    for _line in f.readlines():
        line_num += 1
        (_email, _pw) = _line.split(column_separator, 1)
        if is_email(_email):
            users += [(_email, _pw)]
        else:
            print '[SKIP] line %d: no valid email address: %s' % (line_num, _line)
    f.close()
else:
    usage()

total = len(users)
logger.info('%d users in total.' % total)

count = 1
if backend == 'ldap':
    import ldap
    from libs.ldaplib.ldaputils import convert_keyword_to_dn
    conn = get_db_conn('ldap')

    for (_email, _pw) in users:
        logger.info('(%d/%d) Updating %s' % (count, total, _email))

        dn = convert_keyword_to_dn(_email, accountType='user')
        pw_hash = generate_password_hash(_pw)
        mod_attrs = [(ldap.MOD_REPLACE, 'userPassword', [pw_hash])]
        try:
            conn.modify_s(dn, mod_attrs)
        except Exception, e:
            print '<<< ERROR >>>', e
elif backend in ['mysql', 'pgsql']:
    conn = get_db_conn('vmail')
    for (_email, _pw) in users:
        logger.info('(%d/%d) Updating %s' % (count, total, _email))
        pw_hash = generate_password_hash(_pw)
        conn.update('mailbox',
                    password=pw_hash,
                    where="username='%s'" % _email)
