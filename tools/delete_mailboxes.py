#!/usr/bin/env python

# Author: Zhang Huangbin <zhb@iredmail.org>
# Purpose: Delete mailboxes which are scheduled to be removed.
#
# Notes: iRedAdmin will store maildir path of removed mail users in SQL table
#        `iredadmin.deleted_mailboxes` (LDAP backends) or
#        `vmail.deleted_mailboxes` (SQL backends).
#
# Usage: Either run this script manually, or run it with a daily cron job.
#
#   # python delete_mailboxes.py
#
# Available arguments:
#
#   * --delete-without-timestamp:
#       [RISKY] If no timestamp string in maildir path, continue to delete it.
#
#       With default iRedMail settings, maildir path will contain a timestamp
#       like this: <domain.com>/u/s/e/username-<20160817095303>/
#       (20160817095303 is the timestamp), this way all created maildir paths
#       are unique, even if you removed the user and recreate it with same
#       mail address.
#
#       Without timestamp in maildir path (e.g. <domain.com>/u/s/e/username/),
#       if you removed a user and recreate it someday, this user will see old
#       emails in old mailbox (because maildir path is same as old user's). So
#       it becomes RISKY to remove the mailbox if no timestamp in maildir path.
#
#   * --delete-null-date:
#       Delete mailbox if SQL column `deleted_mailboxes.delete_date` is null.
#
#   * --debug: print additional log

import os
import sys
import time
import logging
import shutil
import pwd
import web

os.environ['LC_ALL'] = 'C'

rootdir = os.path.abspath(os.path.dirname(__file__)) + '/../'
sys.path.insert(0, rootdir)

from tools import ira_tool_lib
import settings

web.config.debug = ira_tool_lib.debug
logger = ira_tool_lib.logger

if '--debug' in sys.argv:
    logger.setLevel(logging.DEBUG)

# Delete if `deleted_mailboxes.delete_date` is null.
delete_null_date = False
if '--delete-null-date' in sys.argv:
    delete_null_date = True

# Make sure there's a timestamp (yyyy.mm.dd.hh.mm.ss) in maildir path,
# otherwise it's too risky to remove this mailbox -- because the maildir
# could be reused by another user after old account was removed.
#
#   - Safe to remove: <domain.com>/u/s/e/username-<timestamp>/
#   - Dangerous to remove: <domain.com>/u/s/e/username/
delete_without_timestamp = False
if '--delete-without-timestamp' in sys.argv:
    delete_without_timestamp = True

def delete_record(conn, rid):
    try:
        conn.delete('deleted_mailboxes',
                    vars={'id': rid},
                    where='id = $id')
        return (True, )
    except Exception, e:
        return (False, repr(e))


def delete_mailbox(conn, record):
    rid = record.id
    username = str(record.username)
    maildir = record.maildir
    timestamp = str(record.timestamp)
    delete_date = record.delete_date

    if not delete_without_timestamp:
        _dir = maildir.rstrip('/')

        if len(_dir) <= 21:
            # Why 21 chars:
            #   - 20 chars: "-<timestamp>". e.g. "-2014.03.26.15.07.25"
            #   - username contains at least 1 char
            logger.error("<<< SKIP >>> Seems no timestamp in maildir path (%s), too risky to remove this mailbox." % maildir)
            return False

        try:
            # Extract timestamp string, make sure it's a valid time format.
            ts = _dir[-19:]
            time.strptime(ts, '%Y.%m.%d.%H.%M.%S')
        except Exception, e:
            logger.error("<<< ERROR >>> Cannot convert timestamp in maildir path, skip." % maildir)
            return False

    # check directory
    if os.path.isdir(maildir):
        # Make sure directory is owned by vmail:vmail
        _dir_stat = os.stat(maildir)
        _dir_uid = _dir_stat.st_uid

        # Get uid/gid of vmail user
        owner = pwd.getpwuid(_dir_uid).pw_name
        if owner != 'vmail':
            logger.error('<<< ERROR >> Directory is not owned by `vmail` user: uid -> %d, user -> %s.' % (_dir_uid, owner))
            return False

        try:
            msg = 'Deleted mailbox (%s): %s.' % (username, maildir)
            msg += ' Account was deleted at %s.' % (timestamp)
            if delete_date:
                msg += ' Mailbox was scheduled to be removed on %s.' % (delete_date)
            else:
                msg += ' Mailbox was scheduled to be removed as soon as possible.'

            logger.info(msg)

            # Delete mailbox
            shutil.rmtree(maildir)

            # Log this deletion.
            ira_tool_lib.log_to_iredadmin(msg,
                                          admin='cron_delete_mailboxes',
                                          username=username,
                                          event='delete_mailboxes')
        except Exception, e:
            logger.error('<<< ERROR >> while deleting mailbox (%s -> %s): %s' % (username, maildir, repr(e)))

    # Delete record.
    delete_record(conn=conn, rid=rid)


# Establish SQL connection.
try:
    if settings.backend == 'ldap':
        conn = ira_tool_lib.get_db_conn('iredadmin')
    else:
        conn = ira_tool_lib.get_db_conn('vmail')
except Exception, e:
    sys.exit('<<< ERROR >>> Cannot connect to SQL database, aborted. Error: %s' % repr(e))

# Get pathes of all maildirs.
sql_where = 'delete_date <= %s' % web.sqlquote(web.sqlliteral('NOW()'))
if delete_null_date:
    sql_where = '(delete_date <= %s) OR (delete_date IS NULL)' % web.sqlquote(web.sqlliteral('NOW()'))

qr = conn.select('deleted_mailboxes', where=sql_where)

if qr:
    logger.info('Delete old mailboxes (%d in total).' % len(qr))
else:
    logger.debug('No mailbox is scheduled to be removed.')

    if not delete_null_date:
        logger.debug("To remove mailboxes with empty schedule date, please run this script with argument '--delete-null-date'.")

    if not delete_without_timestamp:
        logger.debug("To remove mailboxes which don't contain a timesamp in maildir path, please run this script with argument '--delete-without-timestamp'.")

    sys.exit()

for r in list(qr):
    delete_mailbox(conn=conn, record=r)
