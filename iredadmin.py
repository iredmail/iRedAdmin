# encoding: utf-8

# Author: Zhang Huangbin <zhb@iredmail.org>

import os
import sys

rootdir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, rootdir)
from libs import iredbase

# start app
app = iredbase.app

if __name__ == '__main__':
    # Starting webpy builtin http server.
    app.run()
else:
    # Run app under Apache + mod_wsgi.
    application = app.wsgifunc()
