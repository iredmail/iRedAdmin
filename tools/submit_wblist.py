# Author: Zhang Huangbin <zhb@iredmail.org>

# TODO:
#   - able to remove white/blacklist sender addresses
#   - able to specify recipient
#   - able to list all white/blacklists

# Usage:
#
#   # python blacklist_ip.py x.x.x.x y.y.y.y user@domain.com @test.com @.example.com

import os
import sys
import web

os.environ['LC_ALL'] = 'C'

rootdir = os.path.abspath(os.path.dirname(__file__)) + '/../'
sys.path.insert(0, rootdir)

from libs.amavisd import is_valid_amavisd_address, wblist
from tools import ira_tool_lib

web.config.debug = ira_tool_lib.debug
logger = ira_tool_lib.logger

if not len(sys.argv) >= 3:
    sys.exit()
else:
    action = sys.argv[1]
    wb = [v for v in sys.argv[2:] if is_valid_amavisd_address(v)]

    if not action in ['--whitelist', '--blacklist']:
        sys.exit('Invalid action (%s), must be --whitelist or --blacklist' % action)

    if not wb:
        sys.exit('No valid white/blacklist.')

    wl = []
    bl = []
    if action == '--whitelist':
        wl = wb
        logger.info('Submitting whitelist sender address(es): %s' % str(wb))
    elif action == '--blacklist':
        bl = wb
        logger.info('Submit blacklist sender address(es): %s' % str(wb))

logger.info('Establish SQL connection.')
conn = ira_tool_lib.get_db_conn('amavisd')

try:
    wb = wblist.WBList()
    wb.add_wblist(account='@.',
                  wl_senders=wl,
                  bl_senders=bl,
                  flush_before_import=False)
except Exception, e:
    logger.info(str(e))

logger.info('DONE')
