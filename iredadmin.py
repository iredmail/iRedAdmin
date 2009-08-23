#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import os, sys
import web

rootdir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, rootdir)
from libs import iredbase

# start app
app = iredbase.app
web.notfound = iredbase.notfound

if __name__ == '__main__':
    # Use webpy builtin http server.
    app.run()
else:
    # Run app under Apache + mod_wsgi.
    application = app.wsgifunc() 
