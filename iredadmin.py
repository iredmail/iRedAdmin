#!/usr/bin/env python
# Author: Zhang Huangbin <zhb@iredmail.org>

import os
import sys

rootdir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, rootdir)
from libs import iredbase

# Initialize webpy app.
app = iredbase.app

if __name__ != '__main__':
    # Run app under Apache + mod_wsgi.
    application = app.wsgifunc()
else:
    # Starting webpy builtin http server.
    app.run()
