# Author: Zhang Huangbin <zhb@iredmail.org>

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
conn.query('''
    DELETE FROM msgrcpt
    WHERE NOT EXISTS (SELECT 1 FROM msgs WHERE mail_id=msgrcpt.mail_id)
    '''
)

logger.info('Delete unreferenced records from table `quarantine`.')
conn.query('''
    DELETE FROM quarantine
    WHERE NOT EXISTS (SELECT 1 FROM msgs WHERE mail_id=quarantine.mail_id)
    '''
)

logger.info('Delete unreferenced records from table `maddr`.')
conn.query('''
    DELETE FROM maddr
    WHERE NOT EXISTS (SELECT 1 FROM msgs WHERE sid=id)
        AND NOT EXISTS (SELECT 1 FROM msgrcpt WHERE rid=id)
    '''
)

logger.info('Delete unreferenced records from table `mailaddr`.')
conn.query('''DELETE FROM mailaddr WHERE NOT EXISTS (SELECT 1 FROM wblist WHERE sid=id)''')

if counter_msgs or counter_msgrcpt:
    msg = 'Cleanup Amavisd database: delete %d records in msgs, %d in msgrcpt.' % (counter_msgs, counter_msgrcpt)
    ira_tool_lib.log_to_iredadmin(msg, admin='cleanup_amavisd_db', event='cleanup_db')
    logger.info('Log cleanup status.')
