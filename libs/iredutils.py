# encoding: utf-8
# Author: Zhang Huangbin <zhb@iredmail.org>

from os import urandom, getloadavg
import re
import time
import urllib2
import socket
from base64 import b64encode, b64decode
from xml.dom.minidom import parseString as parseXMLString
import random
import subprocess
import web
import settings
from libs import md5crypt

######################
# Regular expressions.
#
# Email.
reEmail = r'''[\w\-][\w\-\.\+\=]*@[\w\-][\w\-\.]*\.[a-zA-Z0-9\-]{2,15}'''

# Domain.
reDomain = r'''[\w\-][\w\-\.]*\.[a-z0-9\-]{2,15}'''

# End Regular expressions.
####

#####################################
# Pre-defined values of SQL functions.
sqlUnixTimestamp = web.sqlliteral('UNIX_TIMESTAMP()')

#####

##############
# Validators
#
INVALID_EMAIL_CHARS = '~!#$%^&*()\\/\ '
INVALID_DOMAIN_CHARS = '~!#$%^&*()+\\/\ '


def is_email(s):
    s = str(s)
    if len(set(s) & set(INVALID_EMAIL_CHARS)) > 0 \
       or '.' not in s \
       or s.count('@') != 1:
        return False

    reCompEmail = re.compile(reEmail + '$', re.IGNORECASE)
    if reCompEmail.match(s):
        return True
    else:
        return False


def is_domain(s):
    s = str(s)
    if len(set(s) & set(INVALID_DOMAIN_CHARS)) > 0 or '.' not in s:
        return False

    reCompDomain = re.compile(reDomain + '$', re.IGNORECASE)
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

    ret = '0'
    if bytes < base:
        ret = '%d Bytes' % (bytes)
    elif bytes < base * base:
        ret = '%d KB' % (bytes / base)
    elif bytes < base * base * base:
        ret = '%d MB' % (bytes / (base * base))
    elif bytes < base * base * base * base:
        if bytes % (base * base * base) == 0:
            ret = '%d GB' % (bytes / (base * base * base))
        else:
            ret = "%d MB" % (bytes / (base * base))
    else:
        ret = '%.1f TB' % (bytes / (base * base * base * base))

    return ret


def set_datetime_format(t, hour=True,):
    """Format LDAP timestamp and Amavisd msgs.time_iso to YYYY-MM-DD HH:MM:SS.

    >>> set_datetime_format('20100925T113256Z')
    '2010-09-25 11:32:56'

    >>> set_datetime_format('20100925T113256Z', hour=False)
    '2010-09-25'

    >>> set_datetime_format('INVALID_TIME_STAMP')      # Return original string
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
        except:
            pass

    # MySQL TIMESTAMP(): yyyymmddTHHMMSSZ
    if 'T' in t and t.endswith('Z'):
        try:
            return time.strftime(time_format, time.strptime(t, '%Y%m%dT%H%M%SZ'))
        except:
            pass

    # MySQL NOW(): yyyy-mm-dd HH:MM:SS
    if '-' in t and ' ' in t and ':' in t:
        # DBMail default last login date.
        if t == '1979-11-03 22:05:58':
            return '--'

        try:
            return time.strftime(time_format, time.strptime(t, '%Y-%m-%d %H:%M:%S'))
        except:
            pass

    # ISO8601 UTC ascii time. Used in table: amavisd.msgs.
    if len(t) == 14:
        try:
            return time.strftime(time_format, time.strptime(t, '%Y%m%d%H%M%S'))
        except:
            pass

    return t


def cut_string(s, length=40):
    try:
        if len(s) != len(s.encode('utf-8', 'replace')):
            length = length / 2

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

def get_server_uptime():
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


def get_system_load_average():
    try:
        (a1, a2, a3) = getloadavg()
        a1 = '%.3f' % a1
        a2 = '%.3f' % a2
        a3 = '%.3f' % a3
        return (a1, a2, a3)
    except:
        return (0, 0, 0)


def get_gmttime():
    # Convert local time to UTC
    return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())


def convertSQLQueryRecords(qr=[]):
    """Convert SQL record value to avoid incorrect unicode handle in Jinja2.

    >>> db = web.DB(None, {})
    >>> qr = db.query('SELECT * FROM msgs')
    >>> convertSQLQueryRecords(qr)

    >>> qr = db.select('msgs')
    >>> convertSQLQueryRecords(qr)
    """
    rcds = []
    for record in qr:
        for k in record:
            try:
                record[k] = web.safeunicode(record.get(k))
            except UnicodeDecodeError:
                record[k] = '<<< DECODE FAILED >>>'
        rcds += [record]
    return rcds


def verify_new_password(newpw, confirmpw,
                        min_passwd_length=settings.min_passwd_length,
                        max_passwd_length=settings.max_passwd_length):
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


def generate_random_strings(length=10):
    """Create a random password of specified length"""
    try:
        length = int(length) or 10
    except:
        length = 10

    # Characters used to generate the random password
    chars = '23456789' + 'abcdefghjkmnpqrstuvwxyz' + '23456789' + \
            'ABCDEFGHJKLMNPQRSTUVWXYZ' + '23456789'     # + '@#&*-+'

    return "".join(random.choice(chars) for x in range(length))


def generate_bcrypt_password(p):
    try:
        import bcrypt
    except:
        return generate_ssha_password(p)

    return '{CRYPT}' + bcrypt.hashpw(p, bcrypt.gensalt())


def verify_bcrypt_password(challenge_password, plain_password):
    try:
        import bcrypt
    except:
        return False

    if challenge_password.startswith('{CRYPT}$2a$') \
       or challenge_password.startswith('{CRYPT}$2b$') \
       or challenge_password.startswith('{crypt}$2a$') \
       or challenge_password.startswith('{crypt}$2b$'):
        challenge_password = challenge_password[7:]
    elif challenge_password.startswith('{BLF-CRYPT}') \
            or challenge_password.startswith('{blf-crypt}'):
        challenge_password = challenge_password[11:]

    return bcrypt.checkpw(plain_password, challenge_password)


def generate_md5_password(p):
    p = str(p).strip()
    return md5crypt.unix_md5_crypt(p, generate_random_strings(length=8))


def verify_md5_password(challenge_password, plain_password):
    """Verify salted MD5 password"""
    if challenge_password.startswith('{MD5}') or challenge_password.startswith('{md5}'):
        challenge_password = challenge_password[5:]
    elif challenge_password.startswith('{CRYPT}') or challenge_password.startswith('{crypt}'):
        challenge_password = challenge_password[7:]

    if not (challenge_password.startswith('$') and
            len(challenge_password) == 34 and
            challenge_password.count('$') == 3):
        return False

    # Get salt from hashed string
    salt = challenge_password.split('$')
    salt[-1] = ''
    salt = '$'.join(salt)

    if md5crypt.md5crypt(plain_password, salt) == challenge_password:
        return True
    else:
        return False

def generate_plain_md5_password(p):
    p = str(p).strip()
    try:
        from hashlib import md5
        return md5(p).hexdigest()
    except ImportError:
        import md5
        return md5.new(p).hexdigest()

    return p


def verify_plain_md5_password(challenge_password, plain_password):
    if challenge_password.startswith('{PLAIN-MD5}') \
       or challenge_password.startswith('{plain-md5}'):
        challenge_password = challenge_password[11:]

    if challenge_password == generate_plain_md5_password(plain_password):
        return True
    else:
        return False

def generate_ssha_password(p):
    p = str(p).strip()
    salt = urandom(8)
    try:
        from hashlib import sha1
        pw = sha1(p)
    except ImportError:
        import sha
        pw = sha.new(p)
    pw.update(salt)
    return "{SSHA}" + b64encode(pw.digest() + salt)


def verify_ssha_password(challenge_password, plain_password):
    """Verify SSHA (salted SHA) hash with or without prefix '{SSHA}'"""
    if challenge_password.startswith('{SSHA}') \
       or challenge_password.startswith('{ssha}'):
        challenge_password = challenge_password[6:]

    if not len(challenge_password) > 20:
        # Not a valid SSHA hash
        return False

    try:
        challenge_bytes = b64decode(challenge_password)
        digest = challenge_bytes[:20]
        salt = challenge_bytes[20:]
        try:
            from hashlib import sha1
            hr = sha1(plain_password)
        except ImportError:
            import sha
            hr = sha.new(plain_password)
        hr.update(salt)
        return digest == hr.digest()
    except:
        return False


def generate_ssha512_password(p):
    """Generate salted SHA512 password with prefix '{SSHA512}'.
    Return salted SHA hash if python is older than 2.5 (module hashlib)."""
    p = str(p).strip()
    try:
        from hashlib import sha512
        salt = urandom(8)
        pw = sha512(p)
        pw.update(salt)
        return "{SSHA512}" + b64encode(pw.digest() + salt)
    except ImportError:
        # Use SSHA password instead if python is older than 2.5.
        return generate_ssha_password(p)


def verify_ssha512_password(challenge_password, plain_password):
    """Verify SSHA512 password with or without prefix '{SSHA512}'.
    Python-2.5 is required since it requires module hashlib."""
    if challenge_password.startswith('{SSHA512}') \
       or challenge_password.startswith('{ssha512}'):
        challenge_password = challenge_password[9:]

    # With SSHA512, hash itself is 64 bytes (512 bits/8 bits per byte),
    # everything after that 64 bytes is the salt.
    if not len(challenge_password) > 64:
        return False

    try:
        challenge_bytes = b64decode(challenge_password)
        digest = challenge_bytes[:64]
        salt = challenge_bytes[64:]

        from hashlib import sha512
        hr = sha512(plain_password)
        hr.update(salt)

        return digest == hr.digest()
    except:
        return False


def generate_cram_md5_password(p):
    """Generate CRAM-MD5 hash with `doveadm pw` command with prefix '{CRAM-MD5}'.
    Return SSHA instead if no 'doveadm' command found or other error raised."""
    p = str(p).strip()

    try:
        pp = subprocess.Popen(['doveadm', 'pw', '-s', 'CRAM-MD5', '-p', p],
                              stdout=subprocess.PIPE)
        return pp.communicate()[0]
    except:
        return generate_ssha_password(p)


def verify_cram_md5_password(challenge_password, plain_password):
    """Verify CRAM-MD5 hash with 'doveadm pw' command."""
    if not challenge_password.startswith('{CRAM-MD5}') \
       or not challenge_password.startswith('{cram-md5}'):
        return False

    try:
        exit_status = subprocess.call(['doveadm',
                                       'pw',
                                       '-t',
                                       challenge_password,
                                       '-p',
                                       plain_password])
        if exit_status == 0:
            return True
    except:
        pass

    return False


def generate_password_hash(p, pwscheme=None):
    """Generate password for LDAP mail user and admin."""
    pw = str(p).strip()

    if not pwscheme:
        pwscheme = settings.DEFAULT_PASSWORD_SCHEME

    if pwscheme == 'BCRYPT':
        pw = generate_bcrypt_password(p)
    elif pwscheme == 'SSHA512':
        pw = generate_ssha512_password(p)
    elif pwscheme == 'SSHA':
        pw = generate_ssha_password(p)
    elif pwscheme == 'MD5':
        pw = '{CRYPT}' + generate_md5_password(p)
    elif pwscheme == 'PLAIN-MD5':
        pw = generate_plain_md5_password(p)
    elif pwscheme == 'PLAIN':
        if settings.SQL_PASSWORD_PREFIX_SCHEME is True:
            pw = '{PLAIN}' + p
        else:
            pw = p
    else:
        # Plain password
        pw = p

    return pw


def verify_password_hash(challenge_password, plain_password):
    # Check plain password and MD5 first.
    if challenge_password in [plain_password,
                              '{PLAIN}' + plain_password,
                              '{plain}' + plain_password]:
        return True
    elif verify_md5_password(challenge_password, plain_password):
        return True

    upwd = challenge_password.upper()
    if upwd.startswith('{SSHA}'):
        return verify_ssha_password(challenge_password, plain_password)
    elif upwd.startswith('{SSHA512}'):
        return verify_ssha512_password(challenge_password, plain_password)
    elif upwd.startswith('{PLAIN-MD5}'):
        return verify_plain_md5_password(challenge_password, plain_password)
    elif upwd.startswith('{CRAM-MD5}'):
        return verify_cram_md5_password(challenge_password, plain_password)
    elif upwd.startswith('{CRYPT}$2A$') or \
            upwd.startswith('{CRYPT}$2B$') or \
            upwd.startswith('{BLF-CRYPT}'):
        return verify_bcrypt_password(challenge_password, plain_password)

    return False


def generate_maildir_path(mail,
                          hash_maildir=settings.MAILDIR_HASHED,
                          prepend_domain_name=settings.MAILDIR_PREPEND_DOMAIN,
                          append_timestamp=settings.MAILDIR_APPEND_TIMESTAMP):
    """Generate path of mailbox."""

    mail = web.safestr(mail)
    if not is_email(mail):
        return (False, 'INVALID_EMAIL_ADDRESS')

    # Get user/domain part from mail address.
    username, domain = mail.split('@', 1)

    # Get current timestamp.
    timestamp = ''
    if append_timestamp:
        timestamp = time.strftime('-%Y.%m.%d.%H.%M.%S')

    if hash_maildir:
        if len(username) >= 3:
            chars = [username[0], username[1], username[2]]

        elif len(username) == 2:
            chars = [username[0], username[1], username[1]]
        else:
            chars = [username[0], username[0], username[0]]

        # Replace '.' by '_'
        for (index, char) in enumerate(chars):
            if char == '.':
                chars[index] = '_'

        maildir = "%s/%s/%s/%s%s/" % (chars[0], chars[1], chars[2], username, timestamp)
    else:
        maildir = "%s%s/" % (username, timestamp)

    if prepend_domain_name:
        maildir = domain + '/' + maildir

    return maildir.lower()


def getNewVersion(urlOfXML):
    '''Checking new version via parsing XML string to extract version number.

    >>> getNewVersion('http://xxx/sample.xml')  # New version available.
    (True, {'version': '1.3.0',
            'date': '2010-10-01',
            'url': 'http://xxx/release-notes-1.3.0.html'
            })

    >>> getNewVersion('http://xxx/sample.xml')  # Error while checking.
    (False, 'HTTP Error 404: Not Found')
    '''

    try:
        socket.setdefaulttimeout(5)
        dom = parseXMLString(urllib2.urlopen(urlOfXML).read())

        version = dom.documentElement.getElementsByTagName('version')[0].childNodes[0].data
        date = dom.documentElement.getElementsByTagName('date')[0].childNodes[0].data
        urlOfReleaseNotes = dom.documentElement.getElementsByTagName('releasenotes')[0].childNodes[0].data

        d = {'version': str(version),
             'date': str(date),
             'url': str(urlOfReleaseNotes)}
        return (True, d)
    except Exception, e:
        return (False, str(e))


def get_iredmail_version():
    v = 'Unknown, check /etc/iredmail-release please.'

    # Read first word splited by space in first line.
    try:
        f = open('/etc/iredmail-release', 'r')
        vline = f.readline().split()
        f.close()

        if vline:
            v = vline[0]
    except:
        pass

    return v
