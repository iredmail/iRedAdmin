#!/usr/bin/env python

# Author: Zhang Huangbin <zhb@iredmail.org>
# Purpose: Remove old records in Amavisd database.

# USAGE:
#
#   1: Make sure you have correct database settings in iRedAdmin config file
#      'settings.py' for Amavisd.
#
#   2: Make sure you have proper values for below two parameters:
#
#       AMAVISD_REMOVE_MAILLOG_IN_DAYS = 7
#       AMAVISD_REMOVE_QUARANTINED_IN_DAYS = 7
#
#      Default values is defined in libs/default_settings.py, you can override
#      them in settings.py. WARNING: DO NOT MODIFY libs/default_settings.py.
#
#   3: Test this script in command line directly, make sure no errors in output
#      message.
#
#       # python cleanup_amavisd_db.py
#
#   4: Setup a daily cron job to execute this script. For example: execute
#      it daily at 1:30AM.
#
#       30  1   *   *   *   python /path/to/cleanup_amavisd_db.py >/dev/null
#
# That's all.

import os
import sys
import web

os.environ['LC_ALL'] = 'C'

rootdir = os.path.abspath(os.path.dirname(__file__)) + '/../'
sys.path.insert(0, rootdir)

import settings
from tools import ira_tool_lib

web.config.debug = ira_tool_lib.debug
logger = ira_tool_lib.logger

backend = settings.backend
logger.info('Backend: %s' % backend)
logger.info('SQL server: %s:%d' % (settings.amavisd_db_host, int(settings.amavisd_db_port)))

query_size_limit = 100
keep_quar_days = settings.AMAVISD_REMOVE_QUARANTINED_IN_DAYS
keep_inout_days = settings.AMAVISD_REMOVE_MAILLOG_IN_DAYS

conn = ira_tool_lib.get_db_conn('amavisd')

# Removing records from single table.
def remove_from_one_table(conn, sql_table, index_column, removed_values):
    total = len(removed_values)

    # Delete 1000 records each time
    offset = 1000

    if total:
        loop_times = total / offset
        if total % offset:
            loop_times += 1

        for i in range(loop_times):
            removing_values = removed_values[offset*i: offset*(i+1)]
            logger.info('\t[-] Deleting records from table `%s`: %d - %d' % (sql_table, i*offset, i*offset + len(removing_values)))
            conn.delete(sql_table,
                        vars={'ids': removing_values},
                        where='%s IN $ids' % index_column)


# Delete old quarantined mails from table 'msgs'. It will also
# delete records in table 'quarantine'.
logger.info('Delete quarantined mails which older than %d days' % keep_quar_days)

if ira_tool_lib.sql_dbn == 'mysql':
    sql_where = """quar_type = 'Q'
                   AND time_num < UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL %d DAY))""" % keep_quar_days
elif ira_tool_lib.sql_dbn == 'postgres':
    sql_where = """quar_type = 'Q'
                   AND time_iso < CURRENT_TIMESTAMP - INTERVAL '%d DAYS'""" % keep_quar_days

counter_msgs = 0
while True:

    qr = conn.select('msgs',
                     what='mail_id',
                     where=sql_where,
                     limit=query_size_limit)

    if qr:
        ids = [id.mail_id for id in qr]
        _total = len(ids)

        logger.info('\t[-] Deleting records: %d - %d' % (counter_msgs+1, counter_msgs + _total))

        conn.delete('msgs', vars={'ids': ids}, where='mail_id IN $ids')
        conn.delete('msgrcpt', vars={'ids': ids}, where='mail_id IN $ids')

        counter_msgs += len(ids)
    else:
        break

logger.info('Delete incoming/outgoing emails which older than %d days' % keep_inout_days)

if ira_tool_lib.sql_dbn == 'mysql':
    sql_where = """quar_type <> 'Q'
                   AND time_num < UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL %d DAY))""" % keep_inout_days
elif ira_tool_lib.sql_dbn == 'postgres':
    sql_where = """quar_type <> 'Q'
                   AND time_iso < CURRENT_TIMESTAMP - INTERVAL '%d DAYS'""" % keep_inout_days

counter_msgrcpt = 0
while True:
    qr = conn.select('msgs',
                     what='mail_id',
                     where=sql_where,
                     limit=query_size_limit)

    if qr:
        ids = [id.mail_id for id in qr]
        _total = len(ids)

        logger.info('\t[-] Deleting records: %d - %d' % (counter_msgrcpt+1, counter_msgrcpt + _total))

        conn.delete('msgs', vars={'ids': ids}, where='mail_id IN $ids')
        conn.delete('msgrcpt', vars={'ids': ids}, where='mail_id IN $ids')

        counter_msgrcpt += _total
    else:
        break

# delete unreferenced records from tables msgrcpt, quarantine and maddr
logger.info('Delete unreferenced records from table `msgrcpt`.')
conn.query('''DELETE FROM msgrcpt
              WHERE NOT EXISTS (SELECT 1 FROM msgs WHERE mail_id=msgrcpt.mail_id)
           ''')

#
# Delete unreferenced records from table `quarantine`.
#
logger.info('Delete unreferenced records from table `quarantine`.')
msgs_mail_ids = set()
maddr_ids_in_use = set()
quar_mail_ids = set()

qr = conn.select('msgs', what='mail_id, sid')
for i in qr:
    msgs_mail_ids.add(i.mail_id)
    maddr_ids_in_use.add(i.sid)

qr = conn.select('quarantine', what='mail_id')
for i in qr:
    quar_mail_ids.add(i.mail_id)

invalid_quar_mail_ids = [id for id in quar_mail_ids if id not in msgs_mail_ids]
remove_from_one_table(conn=conn,
                      sql_table='quarantine',
                      index_column='mail_id',
                      removed_values=invalid_quar_mail_ids)

#
# Delete unreferenced records from table `maddr`.
#
logger.info('Delete unreferenced records from table `maddr`.')

# Get all maddr.id
maddr_ids = set()
qr = conn.select('maddr', what='id')
for i in qr:
    maddr_ids.add(i.id)

qr = conn.select('msgrcpt', what='rid')
for i in qr:
    maddr_ids_in_use.add(i.rid)

invalid_maddr_ids = [id for id in maddr_ids if id not in maddr_ids_in_use]
remove_from_one_table(conn=conn,
                      sql_table='maddr',
                      index_column='id',
                      removed_values=invalid_maddr_ids)

#
# Delete unreferenced records from table `mailaddr`.
#
logger.info('Delete unreferenced records from table `mailaddr`.')

# Get all `mailaddr.id`
mailaddr_ids = set()
qr = conn.select('mailaddr', what='id')
for i in qr:
    mailaddr_ids.add(i.id)

# Get all `wblist.sid` and `outbound_wblist.rid` (both refer to `mailaddr.id`)
wblist_ids = set()

qr = conn.select('wblist', what='sid')
for i in qr:
    wblist_ids.add(i.sid)

try:
    qr = conn.select('outbound_wblist', what='rid')
    for i in qr:
        wblist_ids.add(i.rid)
except:
    # No outbound_wblist table
    pass

invalid_mailaddr_ids = [id for id in mailaddr_ids if id not in wblist_ids]
remove_from_one_table(conn=conn,
                      sql_table='mailaddr',
                      index_column='id',
                      removed_values=invalid_mailaddr_ids)

logger.info('')
logger.info('Remained records:')
logger.info('')
logger.info('      `msgs`: %-7.d' % len(msgs_mail_ids))
logger.info('`quarantine`: %-7.d' % (len(quar_mail_ids) - len(invalid_quar_mail_ids)))
logger.info('     `maddr`: %-7.d' % (len(maddr_ids) - len(invalid_maddr_ids)))
logger.info('  `mailaddr`: %-7.d' % (len(mailaddr_ids) - len(invalid_mailaddr_ids)))


if counter_msgs \
   or counter_msgrcpt \
   or invalid_quar_mail_ids \
   or invalid_maddr_ids \
   or invalid_mailaddr_ids:
    msg = 'Removed records: '
    msg += '%d in msgs, ' % counter_msgs
    msg += '%d in msgrcpt, ' % counter_msgrcpt
    msg += '%d in quarantine, ' % len(invalid_quar_mail_ids)
    msg += '%d in maddr, ' % len(invalid_maddr_ids)
    msg += '%d in mailaddr.' % len(invalid_mailaddr_ids)

    ira_tool_lib.log_to_iredadmin(msg, admin='cleanup_amavisd_db', event='cleanup_db')
    logger.info('Log cleanup status.')
