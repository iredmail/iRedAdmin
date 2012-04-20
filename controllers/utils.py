# Author: Zhang Huangbin <zhb@iredmail.org>

import web


class redirect:
    """Make url ending with or without '/' going to the same class."""
    def GET(self, path):
        raise web.seeother('/' + str(path))


class img:
    def GET(self, encoded_img):
        web.header('Content-Type', 'image/jpeg')
        return encoded_img.decode('base64')


class Expired:
    def GET(self):
        web.header('Content-Type', 'text/html')
        return '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">

    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
        <title>License expired</title>
    </head>

    <body>
        <p>Your license of iRedAdmin-Pro trial edition expired, please <a href="http://www.iredmail.org/admin_buy.html" target="_blank">purchase a license</a> to continue using iRedAdmin-Pro.</p>
    </body>
</html>
'''

