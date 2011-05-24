# encoding: utf-8
# Author: Zhang Huangbin <zhb@iredmail.org>

import gettext
import re
import time
import urllib2
import socket
from xml.dom.minidom import parseString as parseXMLString
import random
import string
import web
from libs import models, md5crypt

cfg = web.iredconfig

##############################################
############## ADDITION SETTINGS #############
##############################################

#############
# Maildir related.
#
#It's RECOMMEND for better performance. Samples:
# - hashed: domain.ltd/u/s/e/username-2009.09.04.12.05.33/
# - non-hashed: domain.ltd/username-2009.09.04.12.05.33/
MAILDIR_HASHED = True

# Prepend domain name in path. Samples:
# - with domain name: domain.ltd/username/
# - without: username/
MAILDIR_PREPEND_DOMAIN = True

# Append timestamp in path. Samples:
# - with timestamp: domain.ltd/username-2010.12.20.13.13.33/
# - without timestamp: domain.ltd/username/
MAILDIR_APPEND_TIMESTAMP = True

####################
# OpenLDAP related.
#

# LDAP connection trace level. Must be an integer.
LDAP_CONN_TRACE_LEVEL = 0

# Default password scheme: SSHA, SHA, PLAIN. Must be a string.
# SSHA is recommended.
LDAP_DEFAULT_PASSWD_SCHEME = 'SSHA'

####################
# MySQL backend related.
#

# Default password scheme: MD5.
# This only impact newly created accounts (admin, user).
SQL_DEFAULT_PASSWD_SCHEME = 'MD5'

########### END ADDITION SETTINGS ############




######################
# Regular expressions.
#
# Email.
reEmail = r"""[\w\-][\w\-\.]*@[\w\-][\w\-\.]+[a-zA-Z]{2,6}"""

# Domain.
reDomain = r"""[\w\-][\w\-\.]*\.[a-z]{2,6}"""

# End Regular expressions.
####

#####################################
# Pre-defined values of SQL functions.
sqlNOW = web.sqlliteral('NOW()')
sqlUnixTimestamp = web.sqlliteral('UNIX_TIMESTAMP()')

#####

##############
# Validators
#
INVALID_EMAIL_CHARS = '~!#$%^&*()+\\/\ '
INVALID_DOMAIN_CHARS = '~!#$%^&*()+\\/\ '

def isEmail(s):
    s = str(s)
    if len(set(s) & set(INVALID_EMAIL_CHARS)) > 0 \
       or '.' not in s \
       or s.count('@') != 1:
        return False

    reCompEmail = re.compile(reEmail, re.IGNORECASE)
    if reCompEmail.match(s):
        return True
    else:
        return False

def isDomain(s):
    s = str(s)
    if len(set(s) & set(INVALID_DOMAIN_CHARS)) > 0:
        return False

    reCompDomain = re.compile(reDomain, re.IGNORECASE)
    if reCompDomain.match(s):
        return True
    else:
        return False

def isStrictIP(s):
    s = str(s)
    fields = s.split('.')
    if len(fields) != 4:
        return False

    # Must be an interger number (0 < number < 255)
    for fld in fields:
        if fld.isdigit():
            if not 0 < int(fld) < 255:
                return False
        else:
            return False

    return True


#
# End Validators
##################


#########################
# Custom Jinja2 filters.
#
def filesizeformat(value, baseMB=False):
    """Format the value like a 'human-readable' file size (i.e. 13 KB,
    4.1 MB, 102 bytes, etc).  Per default decimal prefixes are used (mega,
    giga etc.), if the second parameter is set to `True` the binary
    prefixes are (mebi, gibi).
    """
    try:
        bytes = float(value)
    except:
        return 0

    if baseMB is True:
        bytes = bytes * 1024 * 1024

    base = 1024

    if bytes == 0:
        return '0'

    if bytes < base:
        return "%d Bytes" % (bytes)
    elif bytes < base * base:
        return "%d KB" % (bytes / base)
    elif bytes < base * base * base:
        return "%d MB" % (bytes / (base * base))
    elif bytes < base * base * base * base:
        return "%d GB" % (bytes / (base * base * base))
    return "%.1f TB" % (bytes / (base * base * base * base))


def setDatetimeFormat(t, hour=True,):
    """Format LDAP timestamp and Amavisd msgs.time_iso into YYYY-MM-DD HH:MM:SS.

    >>> setDatetimeFormat('20100925T113256Z')
    '2010-09-25 11:32:56'

    >>> setDatetimeFormat('20100925T113256Z', hour=False)
    '2010-09-25'

    >>> setDatetimeFormat('INVALID_TIME_STAMP')      # Return original string
    'INVALID_TIME_STAMP'
    """
    if t is None:
        return '--'
    else:
        t = str(t)

    if not hour:
        time_format = '%Y-%m-%d'
    else:
        time_format = '%Y-%m-%d %H:%M:%S'

    # LDAP timestamp
    if 'T' not in t and t.endswith('Z'):
        try:
            return time.strftime(time_format, time.strptime(t, '%Y%m%d%H%M%SZ'))
        except Exception, e:
            pass

    # MySQL TIMESTAMP(): yyyymmddTHHMMSSZ
    if 'T' in t and t.endswith('Z'):
        try:
            return time.strftime(time_format, time.strptime(t, '%Y%m%dT%H%M%SZ'))
        except Exception, e:
            pass

    # MySQL NOW(): yyyy-mm-dd HH:MM:SS
    if '-' in t and ' ' in t and ':' in t:
        try:
            return time.strftime(time_format, time.strptime(t, '%Y-%m-%d %H:%M:%S'))
        except Exception, e:
            pass

    # ISO8601 UTC ascii time. Used in table: amavisd.msgs.
    if len(t) == 14:
        try:
            return time.strftime(time_format, time.strptime(t, '%Y%m%d%H%M%S'))
        except Exception, e:
            pass

    return t

def cutString(s, length=40):
    try:
        if len(s) != len(s.encode('utf-8', 'replace')):
            length = length/2

        if len(s) >= length:
            return s[:length] + '...'
        else:
            return s
    except UnicodeDecodeError:
        return unicode(s, 'utf-8', 'replace')
    except:
        return s

#
# End Jinja2 filters.
########################


def getTranslations(lang='en_US'):
    # Init translation.
    if lang in cfg.allTranslations.keys():
        translation = cfg.allTranslations[lang]
    elif lang is None:
        translation = gettext.NullTranslations()
    else:
        try:
            translation = gettext.translation(
                    'iredadmin',
                    cfg['rootdir'] + 'i18n',
                    languages=[lang],
                    )
        except IOError:
            translation = gettext.NullTranslations()
    return translation


def loadTranslations(lang):
    """Return the translations for the locale."""
    lang = str(lang)
    translation = cfg.allTranslations.get(lang)
    if translation is None:
        translation = getTranslations(lang)
        cfg.allTranslations[lang] = translation

        # Delete other translations.
        for lk in cfg.allTranslations.keys():
            if lk != lang:
                del cfg.allTranslations[lk]
    return translation


def iredGettext(string):
    """Translate a given string to the language of the application."""
    lang = web.ctx.lang
    translation = loadTranslations(lang)
    if translation is None:
        return unicode(string)
    return translation.ugettext(string)


def getServerUptime():
    try:
        # Works on Linux.
        f = open("/proc/uptime")
        contents = f.read().split()
        f.close()
    except:
        return None

    total_seconds = float(contents[0])

    MINUTE = 60
    HOUR = MINUTE * 60
    DAY = HOUR * 24

    # Get the days, hours, minutes.
    days = int(total_seconds / DAY)
    hours = int((total_seconds % DAY) / HOUR)
    minutes = int((total_seconds % HOUR) / MINUTE)

    return (days, hours, minutes)


def verifyNewPasswords(newpw, confirmpw, \
                   min_passwd_length=cfg.general.get('min_passwd_length', 0), \
                   max_passwd_length=cfg.general.get('max_passwd_length', 0), \
                  ):
    # Get new passwords from user input.
    newpw = str(newpw).strip()
    confirmpw = str(confirmpw).strip()

    # Empty password is not allowed.
    if newpw == confirmpw:
        passwd = newpw
    else:
        return (False, 'PW_MISMATCH')

    if not len(passwd) > 0:
        return (False, 'PW_EMPTY')

    if not len(passwd) >= int(min_passwd_length):
        return (False, 'PW_LESS_THAN_MIN_LENGTH')

    if int(max_passwd_length) != 0:
        if not len(passwd) <= int(max_passwd_length):
            return (False, 'PW_GREATER_THAN_MAX_LENGTH')

    return (True, passwd)


def getRandomPassword(length=10):
    """Create a random password of specified length"""
    if not str(length).isdigit():
        length = 10
    else:
        length = int(length)

    if length < 10:
        length = 10

    # Characters used to generate the random password
    chars = string.ascii_letters + string.digits #+ '~!@#$%^&*()_+'

    return "".join(random.choice(chars) for x in range(length))


def getMD5Password(p):
    p = str(p).strip()
    return md5crypt.unix_md5_crypt(p, getRandomPassword(length=8))


def getSQLPassword(p):
    if SQL_DEFAULT_PASSWD_SCHEME == 'MD5':
        return getMD5Password(p)
    else:
        # PLAIN text.
        return p


def setMailMessageStore(mail,
                        hashedMaildir=MAILDIR_HASHED,
                        prependDomainName=MAILDIR_PREPEND_DOMAIN,
                        appendTimestamp=MAILDIR_APPEND_TIMESTAMP,
                       ):
    """Generate path of mailbox."""

    mail = web.safestr(mail)
    if not isEmail(mail):
        return (False, 'INVALID_EMAIL_ADDRESS')

    # Get user/domain part from mail address.
    username, domain = mail.split('@', 1)

    # Get current timestamp.
    timestamp = ''
    if appendTimestamp:
        timestamp = time.strftime('-%Y.%m.%d.%H.%M.%S')

    if hashedMaildir is True:
        if len(username) >= 3:
            maildir = "%s/%s/%s/%s%s/" % (username[0], username[1], username[2], username, timestamp,)
        elif len(username) == 2:
            maildir = "%s/%s/%s/%s%s/" % (username[0], username[1], username[1], username, timestamp,)
        else:
            maildir = "%s/%s/%s/%s%s/" % (username[0], username[0], username[0], username, timestamp,)

        mailMessageStore = maildir
    else:
        mailMessageStore = "%s%s/" % (username, timestamp,)

    if prependDomainName:
        mailMessageStore = domain + '/' + mailMessageStore

    return mailMessageStore.lower()


# Return value of percentage.
def getPercentage(molecusar, denominator):
    try:
        molecusar = int(molecusar)
        denominator = int(denominator)
    except:
        return 0

    if molecusar == 0 or denominator == 0:
        return 0
    else:
        percent = (molecusar * 100) // denominator
        if percent < 0:
            return 0
        elif percent > 100:
            return 100
        else:
            return percent


def getNewVersion(urlOfXML):
    '''Checking new version via parsing XML string to extract version number.

    >>> getNewVersion('http://xxx/sample.xml')  # New version available.
    (True, {'version': '1.3.0', 'date': '2010-10-01', 'url': 'http://xxx/release-notes-1.3.0.html'})

    >>> getNewVersion('http://xxx/sample.xml')  # Error while checking.
    (False, 'HTTP Error 404: Not Found')
    '''

    try:
        socket.setdefaulttimeout(5)
        dom = parseXMLString(urllib2.urlopen(urlOfXML).read())

        version = dom.documentElement.getElementsByTagName('version')[0].childNodes[0].data
        date = dom.documentElement.getElementsByTagName('date')[0].childNodes[0].data
        urlOfReleaseNotes = dom.documentElement.getElementsByTagName('releasenotes')[0].childNodes[0].data

        d = {'version': str(version), 'date': str(date), 'url': str(urlOfReleaseNotes),}
        return (True, d)
    except Exception, e:
        return (False, str(e))

############################
# Get real-time used quota.
#
def getAccountUsedQuota(accounts):
    # @accounts: must be list/tuple of email addresses.

    # Pre-defined dict of used quotas.
    #   {'user@domain.ltd': {'bytes': INTEGER, 'messages': INTEGER,}}
    accountUsedQuota = {}

    # Get used quota.
    if len(accounts) > 0:
        try:
            result_used_quota = web.admindb.select(
                models.UsedQuota.__table__,
                where='%s IN %s' % (
                    models.UsedQuota.username,
                    web.sqlquote(accounts),
                ),
                what='%s,%s,%s' % (
                    models.UsedQuota.username,
                    models.UsedQuota.bytes,
                    models.UsedQuota.messages,
                ),
            )

            for uq in result_used_quota:
                accountUsedQuota[uq.get(models.UsedQuota.username)] = {
                    models.UsedQuota.bytes: uq.get(models.UsedQuota.bytes, 0),
                    models.UsedQuota.messages: uq.get(models.UsedQuota.messages, 0),
                }
        except Exception, e:
            pass

    return accountUsedQuota

def deleteAccountFromUsedQuota(accounts):
    # @accounts: must be list/tuple of email addresses.
    if len(accounts) > 0:
        try:
            web.admindb.delete(
                models.UsedQuota.__table__,
                where=' %s IN %s' % (
                    models.UsedQuota.username,
                    web.sqlquote(accounts),
                ),
            )
            return (True,)
        except Exception, e:
            return (False, str(e))
    else:
        return (True,)
