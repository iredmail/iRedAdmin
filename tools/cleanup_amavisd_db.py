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
#       # python /path/to/cleanup_amavisd_db.py
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

query_size_limit = 100

conn = ira_tool_lib.get_db_conn('amavisd')

# Delete old quarantined mails from table 'msgs'. It will also
# delete records in table 'quarantine'.
logger.info('Delete quarantined mails which older than %d days' % settings.AMAVISD_REMOVE_QUARANTINED_IN_DAYS)
counter_msgs = 0
while True:
    if ira_tool_lib.sql_dbn == 'mysql':
        sql_where = """quar_type = 'Q' AND time_num < UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL %d DAY))""" % settings.AMAVISD_REMOVE_QUARANTINED_IN_DAYS
    elif ira_tool_lib.sql_dbn == 'postgres':
        sql_where = """quar_type = 'Q' AND time_iso < CURRENT_TIMESTAMP - INTERVAL '%d DAYS'""" % settings.AMAVISD_REMOVE_QUARANTINED_IN_DAYS
    else:
        break

    qr = conn.select('msgs',
                     what='mail_id',
                     where=sql_where,
                     limit=query_size_limit)

    if qr:
        ids = [id.mail_id for id in qr]

        counter_msgs += len(ids)
        logger.info('[-] Deleting %d records' % counter_msgs)

        conn.delete('msgs', vars={'ids': ids}, where='mail_id IN $ids')
        conn.delete('msgrcpt', vars={'ids': ids}, where='mail_id IN $ids')
    else:
        break

logger.info('Delete incoming/outgoing emails which older than %d days' % settings.AMAVISD_REMOVE_MAILLOG_IN_DAYS)
counter_msgrcpt = 0
while True:
    if ira_tool_lib.sql_dbn == 'mysql':
        sql_where = """quar_type <> 'Q' AND time_num < UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL %d DAY))""" % settings.AMAVISD_REMOVE_MAILLOG_IN_DAYS
    elif ira_tool_lib.sql_dbn == 'postgres':
        sql_where = """quar_type <> 'Q' AND time_iso < CURRENT_TIMESTAMP - INTERVAL '%d DAYS'""" % settings.AMAVISD_REMOVE_MAILLOG_IN_DAYS
    else:
        break

    qr = conn.select('msgs',
                     what='mail_id',
                     where=sql_where,
                     limit=query_size_limit)

    if qr:
        ids = [id.mail_id for id in qr]

        counter_msgrcpt += len(ids)
        logger.info('[-] Deleting %d records' % counter_msgrcpt)

        conn.delete('msgs', vars={'ids': ids}, where='mail_id IN $ids')
        conn.delete('msgrcpt', vars={'ids': ids}, where='mail_id IN $ids')
    else:
        break

# delete unreferenced records from tables msgrcpt, quarantine and maddr
logger.info('Delete unreferenced records from table `msgrcpt`.')
conn.query('''DELETE FROM msgrcpt
              WHERE NOT EXISTS (SELECT 1 FROM msgs WHERE mail_id=msgrcpt.mail_id)
           ''')

logger.info('Delete unreferenced records from table `quarantine`.')
msgs_mail_ids = set()
maddr_ids_in_use = set()
quar_mail_ids = []

qr = conn.select('msgs', what='mail_id, sid')
for i in qr:
    msgs_mail_ids.add(i.mail_id)
    maddr_ids_in_use.add(i.sid)
logger.info('- `msgs` table has %d records' % len(msgs_mail_ids))

qr = conn.select('quarantine', what='mail_id')
for i in qr:
    quar_mail_ids.append(i.mail_id)
logger.info('- `quarantine` table has %d records' % len(quar_mail_ids))

invalid_quar_mail_ids = []
counter = 0
for id in quar_mail_ids:
    if id not in msgs_mail_ids:
        invalid_quar_mail_ids.append(id)
        counter += 1

    if invalid_quar_mail_ids and (counter % 1000 == 0):
        logger.info('[-] Deleting %d unreferenced records in `quarantine` table' % counter)
        conn.delete('quarantine',
                    vars={'ids': invalid_quar_mail_ids},
                    where='mail_id IN $ids')
        invalid_quar_mail_ids = []

del quar_mail_ids
del msgs_mail_ids
del invalid_quar_mail_ids

logger.info('Delete unreferenced records from table `maddr`.')

# Get all maddr.id
maddr_ids = set()
qr = conn.select('maddr', what='id')
for i in qr:
    maddr_ids.add(i.id)
logger.info('- `maddr` contains %d addresses' % len(maddr_ids))

qr = conn.select('msgrcpt', what='rid')
for i in qr:
    maddr_ids_in_use.add(i.rid)
logger.info('- `msgs` and `msgrcpt` have %d addresses' % len(maddr_ids_in_use))

invalid_maddr_ids = []
counter_invalid_maddr_ids = 0
counter = 0
for id in maddr_ids:
    if id not in maddr_ids_in_use:
        invalid_maddr_ids.append(id)
        counter += 1

    if invalid_maddr_ids and (counter % 1000 == 0):
        logger.info('[-] Deleting %d unreferenced records in `maddr` table' % counter)
        conn.delete('maddr',
                    vars={'ids': invalid_maddr_ids},
                    where='id IN $ids')
        invalid_maddr_ids = []

if invalid_maddr_ids:
    counter_invalid_maddr_ids = len(invalid_maddr_ids)
    logger.info('- Removed %d unreferenced addresses in `maddr`' % counter_invalid_maddr_ids)

del invalid_maddr_ids
del maddr_ids_in_use
del maddr_ids

logger.info('Delete unreferenced records from table `mailaddr`.')
# Get all `mailaddr.id`
all_mailaddr_ids = set()
qr = conn.select('mailaddr', what='id')
for i in qr:
    all_mailaddr_ids.add(i.id)
logger.info('- `mailaddr` contains %d addresses' % len(all_mailaddr_ids))

# Get all `wblist.sid` and `outbound_wblist.rid` (both refer to `mailaddr.id`)
wblist_ids = set()

qr = conn.select('wblist', what='sid')
for i in qr:
    wblist_ids.add(i.sid)

try:
    qr = conn.select('outbound_wblist', what='rid')
    for i in qr:
        wblist_ids.add(i.sid)
except:
    # No outbound_wblist table
    pass

logger.info('- `wblist` and `outbound_wblist` contain %d addresses' % len(wblist_ids))

invalid_mailaddr_ids = []
counter_invalid_mailaddr_ids = 0
counter = 0
for id in all_mailaddr_ids:
    if id not in wblist_ids:
        invalid_mailaddr_ids.append(id)
        counter += 1

    if invalid_mailaddr_ids and (counter % 1000 == 0):
        logger.info('[-] Deleting %d unreferenced addresses in `mailaddr`' % counter)
        conn.delete('maddr',
                    vars={'ids': invalid_mailaddr_ids},
                    where='id IN $ids')
        invalid_mailaddr_ids = []

if invalid_mailaddr_ids:
    counter_invalid_mailaddr_ids = len(invalid_mailaddr_ids)
    logger.info('- Removed %d unreferenced addresses in `maddr`' % counter_invalid_mailaddr_ids)

del wblist_ids
del invalid_mailaddr_ids
del all_mailaddr_ids

if counter_msgs or counter_msgrcpt:
    msg = 'Removed %d records in msgs, %d in msgrcpt, %d in maddr, %d in mailaddr.' % (counter_msgs,
                                                                                       counter_msgrcpt,
                                                                                       counter_invalid_maddr_ids,
                                                                                       counter_invalid_mailaddr_ids)
    ira_tool_lib.log_to_iredadmin(msg, admin='cleanup_amavisd_db', event='cleanup_db')
    logger.info('Log cleanup status.')
