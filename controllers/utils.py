# Author: Zhang Huangbin <zhb@iredmail.org>

import simplejson as json
import web


class Redirect:
    """Make url ending with or without '/' going to the same class."""

    def GET(self, path):
        raise web.seeother("/" + str(path))
