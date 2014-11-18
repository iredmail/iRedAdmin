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

# Import addition config file of iRedAdmin-Pro: libs/settings.py.
import settings
from tools import ira_tool_lib

web.config.debug = ira_tool_lib.debug
logger = ira_tool_lib.logger

backend = settings.backend
logger.info('Backend: %s' % backend)

if backend in ['ldap', 'mysql']:
    sql_dbn = 'mysql'
elif backend in ['pgsql']:
    sql_dbn = 'postgres'
else:
    sys.exit('Error: Unsupported backend (%s).' % backend)

conn = web.database(dbn=sql_dbn,
                    host=settings.amavisd_db_host,
                    port=int(settings.amavisd_db_port),
                    db=settings.amavisd_db_name,
                    user=settings.amavisd_db_user,
                    pw=settings.amavisd_db_password)

# Delete old quarantined mails from table 'msgs'. It will also
# delete records in table 'quarantine'.
logger.info('Delete quarantined mails which older than %d days' % settings.AMAVISD_REMOVE_QUARANTINED_IN_DAYS)
if sql_dbn == 'mysql':
    conn.query('''
        DELETE FROM msgs
        WHERE
            quar_type = 'Q'
            AND time_num < UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL %d DAY))
        ''' % settings.AMAVISD_REMOVE_QUARANTINED_IN_DAYS
    )

elif sql_dbn == 'postgres':
    conn.query('''
        DELETE FROM msgs
        WHERE
            quar_type = 'Q'
            AND time_iso < CURRENT_TIMESTAMP - INTERVAL '%d DAYS'
        ''' % settings.AMAVISD_REMOVE_QUARANTINED_IN_DAYS
    )

logger.info('Delete incoming/outgoing emails which older than %d days' % settings.AMAVISD_REMOVE_MAILLOG_IN_DAYS)
if sql_dbn == 'mysql':
    logger.info('+ Delete from table `msgrcpt`.')
    conn.query('''
        DELETE msgrcpt.*
        FROM msgrcpt
        INNER JOIN msgs ON msgrcpt.mail_id=msgs.mail_id
        WHERE msgs.time_num < UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL %d DAY))
        ''' % settings.AMAVISD_REMOVE_MAILLOG_IN_DAYS
    )

    logger.info('+ Delete from table `msgs`.')
    conn.query('''
        DELETE FROM msgs
        WHERE time_num < UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL %d DAY))
        ''' % settings.AMAVISD_REMOVE_MAILLOG_IN_DAYS
    )
elif sql_dbn == 'postgres':
    logger.info('+ Delete from table `msgrcpt`.')
    conn.query('''
        DELETE FROM msgrcpt
        USING msgs
        WHERE
            msgrcpt.mail_id=msgs.mail_id
            AND msgs.time_iso < CURRENT_TIMESTAMP - INTERVAL '%d DAYS'
        ''' % settings.AMAVISD_REMOVE_MAILLOG_IN_DAYS
    )

    logger.info('+ Delete from table `msgs`.')
    conn.query('''
        DELETE FROM msgs
        WHERE time_iso < CURRENT_TIMESTAMP - INTERVAL '%d DAYS'
        ''' % settings.AMAVISD_REMOVE_MAILLOG_IN_DAYS
    )

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
