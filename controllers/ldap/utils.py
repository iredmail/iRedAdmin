#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import web,sys

class img:
    def GET(self, encoded_img):
        web.header('Content-Type', 'image/jpeg')
        return encoded_img.decode('base64')
