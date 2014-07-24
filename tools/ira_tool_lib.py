"""Library used by other scripts under tools/ directory."""

# Author: Zhang Huangbin <zhb@iredmail.org>

import logging

# Set True to print SQL queries.
debug = False

# Config logging
logging.basicConfig(level=logging.INFO,
                    format='* [%(asctime)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                   )

logger = logging.getLogger('iRedAdmin-Pro')
