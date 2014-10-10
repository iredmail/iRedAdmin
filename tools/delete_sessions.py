# Author: Zhang Huangbin <zhb@iredmail.org>
# Purpose: Delete all records in SQL table "iredadmin.sessions" to force
#          all admins to re-login.

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

if settings.backend in ['ldap', 'mysql']:
    sql_dbn = 'mysql'
elif settings.backend in ['pgsql']:
    sql_dbn = 'postgres'
else:
    sys.exit('Error: Unsupported backend (%s).' % settings.backend)

conn = web.database(dbn=sql_dbn,
                    host=settings.iredadmin_db_host,
                    port=int(settings.iredadmin_db_port),
                    db=settings.iredadmin_db_name,
                    user=settings.iredadmin_db_user,
                    pw=settings.iredadmin_db_password)

# Delete old quarantined mails from table 'msgs'. It will also
# delete records in table 'quarantine'.
logger.info('Delete all existing sessions to force admins to re-login.')
conn.query('DELETE FROM sessions')
