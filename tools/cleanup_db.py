#!/usr/bin/env python

# Author: Zhang Huangbin <zhb@iredmail.org>
# Purpose: Remove old records in iRedAdmin SQL database.

# USAGE:
#
#   1: Make sure you have proper values for below two parameters:
#
#       IREDADMIN_LOG_KEPT_DAYS = 30
#
#      Default values is defined in libs/default_settings.py, you can override
#      them in settings.py. WARNING: DO NOT MODIFY libs/default_settings.py.
#
#   2: Test this script in command line directly, make sure no errors in output
#      message.
#
#       # python cleanup_db.py
#
#   3: Setup a daily cron job to execute this script. For example: execute
#      it daily at 1:30AM.
#
#       30  1   *   *   *   python /path/to/cleanup_db.py >/dev/null
#
# That's all.

import os
import sys
import web

os.environ['LC_ALL'] = 'C'

rootdir = os.path.abspath(os.path.dirname(__file__)) + '/../'
sys.path.insert(0, rootdir)

import settings
from tools.ira_tool_lib import debug, logger, sql_dbn, get_db_conn, sql_count_id

web.config.debug = debug

backend = settings.backend
logger.info('Backend: %s' % backend)
logger.info('SQL server: %s:%d' % (settings.iredadmin_db_host, int(settings.iredadmin_db_port)))

query_size_limit = 100
kept_days = settings.IREDADMIN_LOG_KEPT_DAYS

conn_iredadmin = get_db_conn('iredadmin')

logger.info('Delete old admin activity log (> %d days)' % kept_days)

if sql_dbn == 'mysql':
    sql_where = """timestamp < DATE_SUB(NOW(), INTERVAL %d DAY)""" % kept_days
elif sql_dbn == 'postgres':
    sql_where = """timestamp < CURRENT_TIMESTAMP - INTERVAL '%d DAYS'""" % kept_days

total_before = sql_count_id(conn_iredadmin, 'log')
conn_iredadmin.delete('log', where=sql_where)
total_after = sql_count_id(conn_iredadmin, 'log')
logger.info('\t- %d removed, %d left.' % (total_before - total_after, total_after))
