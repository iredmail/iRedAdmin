#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

#---------------------------------------------------------------------
# This file is part of iRedAdmin-OSE, which is official web-based admin
# panel (Open Source Edition) for iRedMail.
#
# iRedMail is an open source mail server solution for Red Hat(R)
# Enterprise Linux, CentOS, Debian and Ubuntu.
#
# iRedAdmin-OSE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# iRedAdmin-OSE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with iRedAdmin-OSE.  If not, see <http://www.gnu.org/licenses/>.
#---------------------------------------------------------------------

import gettext
import os
import re
import web

cfg = web.iredconfig

# Regular expression.
pEmail = r'[\w\-][\w\-\.]*@[\w\-][\w\-\.]+[a-zA-Z]{1,4}'
pQuota = '\d+'

regEmail = re.compile(pEmail)
regQuota = re.compile(pQuota)

def filesizeformat(value):
    """Format the value like a 'human-readable' file size (i.e. 13 KB,
    4.1 MB, 102 bytes, etc).  Per default decimal prefixes are used (mega,
    giga etc.), if the second parameter is set to `True` the binary
    prefixes are (mebi, gibi).
    """
    bytes = float(value)
    base = 1024
    if bytes < base:
        return "%d Bytes" % (bytes, bytes != 1 and 's' or '')
    elif bytes < base * base:
        return "%d KB" % (bytes / base)
    elif bytes < base * base * base:
        return "%d MB" % (bytes / (base * base))
    return "%.1f GB" % (bytes / (base * base * base))

def get_translation(lang):
    # Init translations.
    if lang == 'en_US':
        translations = gettext.NullTranslations()
    else:
        try:
            translations = gettext.translation(
                    'iredadmin',
                    cfg['rootdir'] + 'i18n',
                    languages=[lang],
                    )
        except IOError:
            translations = gettext.NullTranslations()
    return translations

def setRenderLang(renderInst, lang, oldlang=None):
    if oldlang is not None:
        old_translation = get_translation(oldlang)
        renderInst._lookup.uninstall_gettext_translations(old_translation)

    new_translations = get_translation(lang)
    renderInst._lookup.install_gettext_translations(new_translations)
    return renderInst

def getServerUptime():
     try:
         # Works on Linux.
         f = open( "/proc/uptime" )
         contents = f.read().split()
         f.close()
     except:
        return None

     total_seconds = float(contents[0])

     MINUTE  = 60
     HOUR    = MINUTE * 60
     DAY     = HOUR * 24

     # Get the days, hours, minutes.
     days    = int( total_seconds / DAY )
     hours   = int( ( total_seconds % DAY ) / HOUR )
     minutes = int( ( total_seconds % HOUR ) / MINUTE )
     seconds = int( total_seconds % MINUTE )

     return (days, hours, minutes)

def getNewPassword(newpw, confirmpw):
    # Get new passwords from user input.
    newpw = str(newpw)
    confirmpw = str(confirmpw)

    # Empty password is not allowed.
    if newpw == confirmpw:
        passwd = newpw
    else:
        return (False, 'msg=PW_MISMATCH')

    if not len(passwd) > 0:
        return (False, 'msg=PW_EMPTY')

    # Check password length.
    min_passwd_length = cfg.general.get('min_passwd_length', 1)
    max_passwd_length = cfg.general.get('max_passwd_length', 0)

    if not len(passwd) >= int(min_passwd_length):
        return (False, 'msg=PW_LESS_THAN_MIN_LENGTH')

    if int(max_passwd_length) != 0:
        if not len(passwd) <= int(max_passwd_length):
            return (False, 'msg=PW_GREATER_THAN_MAX_LENGTH')

    return (True, passwd)
