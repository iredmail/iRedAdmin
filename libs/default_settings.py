# Author: Zhang Huangbin <zhb@iredmail.org>

#
# WARNING
#
# Please place all your settings in settings.py to override settings below, so
# that you can simply copy settings.py after upgrading iRedAdmin.
#

# Debug iRedAdmin: True, False.
DEBUG = False

# Session timeout in seconds. Default is 30 minutes (1800 seconds).
SESSION_TIMEOUT = 1800

# Mail detail message of '500 internal server error' to webmaster: True, False.
# If set to True, iredadmin will mail detail error to webmaster when
# it catches 'internal server error' via LOCAL mail server to aid
# in debugging production servers.
MAIL_ERROR_TO_WEBMASTER = False

# Set http proxy server address if iRedAdmin cannot access internet
# (iredmail.org) directly.
# Sample:
#   HTTP_PROXY = 'http://192.168.1.1:3128'
HTTP_PROXY = ''

# Local timezone. It must be one of below:
#   GMT-12:00
#   GMT-11:00
#   GMT-10:00
#   GMT-09:30
#   GMT-09:00
#   GMT-08:00
#   GMT-07:00
#   GMT-06:00
#   GMT-05:00
#   GMT-04:30
#   GMT-04:00
#   GMT-03:30
#   GMT-03:00
#   GMT-02:00
#   GMT-01:00
#   GMT
#   GMT+01:00
#   GMT+02:00
#   GMT+03:00
#   GMT+03:30
#   GMT+04:00
#   GMT+04:30
#   GMT+05:00
#   GMT+05:30
#   GMT+05:45
#   GMT+06:00
#   GMT+06:30
#   GMT+07:00
#   GMT+08:00
#   GMT+08:45
#   GMT+09:00
#   GMT+09:30
#   GMT+10:00
#   GMT+10:30
#   GMT+11:00
#   GMT+11:30
#   GMT+12:00
#   GMT+12:45
#   GMT+13:00
#   GMT+14:00
LOCAL_TIMEZONE = 'GMT'

###################################
# General settings
#
# SQL table used to store real-time mailbox quota usage.
#   - For SQL backends, it's stored in SQL db 'vmail'.
#   - For LDAP backend, it's stored in SQL db 'iredadmin'.
SQL_TBL_USED_QUOTA = 'used_quota'

# Default password scheme, must be a string.
#
#   - Available schemes for LDAP backend: BCRYPT, SSHA, PLAIN.
#   - Available schemes for SQL backend: BCRYPT, SSHA, MD5, PLAIN-MD5 (without salt), PLAIN.
#
# Recommended schemes in specified order:
#
#   BCRYPT -> SSHA -> MD5
#
# WARNING: Don't use PLAIN-MD5, PLAIN, they're easy to crack.
#
# Important notes:
#
#   - Password length and complexity are probably more important then a strong
#     crypt algorithm.
#
#   - BCRYPT: *) must be supported by your system's libc.
#                You can get available algorithms with command 'doveadm pw -l'
#                ('BLF-CRYPT' is BCRYPT).
#                Unfortunately, most Linux distributions doesn't support it,
#                but OpenBSD supports it.
#
#             *) BCRYPT is slower than SSHA512, SSHA, MD5.
#                But, "Speed is exactly what you don't want in a password hash function."
#
#   - SSHA512: requires Dovecot-2.0 (and later) and Python-2.5 (and later).
#              If you're running Python-2.4, iRedAdmin will generate SSHA hash
#              instead of SSHA512. But if you're running Dovecot-1.x, user
#              authentication will fail.
#
#   - CRAM-MD5: Currently works with SQL backends, but not LDAP.
#
# Passwords of new mail accounts will be crypted by specified scheme.
# Sample password format:
#
# - BCRYPT: {CRYPT}$2a$05$TKnXV39M3uJ4o.AbY1HbjeAval9bunHbxd0.6Qn782yKoBjTEBXTe
#           NOTE: Use prefix '{CRYPT}' instead of '{BLF-CRYPT}'.
# - SSHA512: {SSHA512}FxgXDhBVYmTqoboW+ibyyzPv/wGG7y4VJtuHWrx+wfqrs/lIH2Qxn2eA0jygXtBhMvRi7GNFmL++6aAZ0kXpcy1fxag=
# - SSHA: {SSHA}bfxqKqOOKODJw/bGqMo54f9Q/iOvQoftOQrqWA==
# - CRAM-MD5: {CRAM-MD5}465076e1c95ac134fc2ba88ad617b6660958f388d60423504ee7c46ce44be8b4
# - MD5: $1$ozdpg0V0$0fb643pVsPtHVPX8mCZYW/
# - PLAIN-MD5: 900150983cd24fb0d6963f7d28e17f72.
# - PLAIN: Plain text.
#
# References:
#
#   - Dovecot password schemes:
#       o Dovecot-1.x: http://wiki.dovecot.org/Authentication/PasswordSchemes
#       o dovecot-2.x: http://wiki2.dovecot.org/Authentication/PasswordSchemes
#
#   - bcrypt:
#       o A Future-Adaptable Password Scheme: http://www.openbsd.org/papers/bcrypt-paper.ps
#       o How to safely store a password. http://codahale.com/how-to-safely-store-a-password/
#
DEFAULT_PASSWORD_SCHEME = 'SSHA'

# Allow to store password in plain text.
# It will show a HTML checkbox to allow admin to store newly created user
# password or reset password in plain text. If not checked, password
# will be stored as encrypted.
STORE_PASSWORD_IN_PLAIN_TEXT = False

# Print PERMISSION_DENIED related programming info to stdout or web server
# log file. e.g. Apache log file.
LOG_PERMISSION_DENIED = False

# Redirect to "Domains and Accounts" page instead of Dashboard.
REDIRECT_TO_DOMAIN_LIST_AFTER_LOGIN = False

###################################
# Maildir related.
#

# It's RECOMMEND for better performance. Samples:
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

#######################################
# LDAP backends related settings.
#
# Define LDAP server product name: OPENLDAP, LDAPD (OpenBSD built-in ldap daemon)
LDAP_SERVER_PRODUCT_NAME = 'OPENLDAP'


# LDAP connection trace level. Must be an integer.
LDAP_CONN_TRACE_LEVEL = 0

#######################################
# MySQL/PostgreSQL backends related settings. Note: Not applicable for DBMail.
#

# Prefix '{PLAIN}' in plain passwords: True, False.
#
# Required by dovecot if you want to store passwords as plain text.
# Password scheme can be overridden for each password by prefixing it with
# {SCHEME}, for example: {PLAIN}my_password.
# It's recommended to prefix it if you have some passwords stored in MD5 or
# other scheme, so that dovecot can detect scheme for each passwords.
SQL_PASSWD_PREFIX_SCHEME = True

# Access policies of mail deliver restrictions. Must be in lower cases.
SQL_ALIAS_ACCESS_POLICIES = [
    'public',       # Unrestricted Everyone can send mail to this address.
    'domain',       # Domain users only.
    'subdomain',    # Domain and sub-domain users only.
    'membersonly',  # Members only
    'allowedonly',  # Moderators only
    'membersandmoderatorsonly',  # Members and moderators only
]

###################################
# Amavisd related settings.
#

# Remove old SQL records of sent/received mails in Amavisd database.
# NOTE: require cron job with script tools/cleanup_amavisd_db.py.
AMAVISD_REMOVE_MAILLOG_IN_DAYS = 3

# Remove old SQL records of quarantined mails.
# Since quarantined mails may take much disk space, it's better to release
# or remove them as soon as possible.
# NOTE: require cron job with script tools/cleanup_amavisd_db.py.
AMAVISD_REMOVE_QUARANTINED_IN_DAYS = 7

# SQL command used to create necessary Amavisd policy for newly created
# mail user.
#
# To execute specified SQL commands without enabling Amavisd integration
# in settings.ini, please set AMAVISD_EXECUTE_SQL_WITHOUT_ENABLED to True,
# and make sure you have correct Amavisd database related settings in
# settings.ini.
#
# Available placeholders:
#   - $mail:     replaced by email address of newly created user
#   - $username: replaced by username part of email address
#   - $domain:   replaced by domain part of email address
#
# For example:
#
#   AMAVISD_SQL_FOR_NEWLY_CREATED_USER = [
#       'INSERT INTO users (priority, policy_id, email) VALUES (0, 5, $mail)',
#       'INSERT INTO users (priority, policy_id, email) VALUES (0, 5, $username)',
#       'INSERT INTO users (priority, policy_id, email) VALUES (0, 5, concat("@", $domain))',
#   ]
#
# Will be replaced by:
#
#   AMAVISD_SQL_FOR_NEWLY_CREATED_USER = [
#       'INSERT INTO users (priority, policy_id, email) VALUES (0, 5, "user@domain.ltd")',
#       'INSERT INTO users (priority, policy_id, email) VALUES (0, 5, "user")',
#       'INSERT INTO users (priority, policy_id, email) VALUES (0, 5, concat("@", "domain.ltd"))',
#   ]
#
AMAVISD_EXECUTE_SQL_WITHOUT_ENABLED = False
AMAVISD_SQL_FOR_NEWLY_CREATED_USER = []

###################################
# iRedAdmin related settings.
#
IREDADMIN_LOG_KEPT_DAYS = 30

###################################
# iRedAPD related settings.
#
# Show how many top senders/recipients on Dashboard page.
NUM_TOP_SENDERS = 10
NUM_TOP_RECIPIENTS = 10

# Count top senders/recipients in last SECONDS (86400 == 1 day)
TIME_LENGTH_OF_TOP_SENDERS = 86400
TIME_LENGTH_OF_TOP_RECIPIENTS = 86400

###################################
# DBMail related settings.
#

# Default domain transport will be stored in `dbmail_domains.transport`.
DBMAIL_DEFAULT_DOMAIN_TRANSPORT = 'dbmail-lmtp:127.0.0.1:24'

# Create and subscribe to default IMAP folders after creating new mail user.
DBMAIL_CREATE_DEFAULT_IMAP_FOLDERS = True
DBMAIL_DEFAULT_IMAP_FOLDERS = ['INBOX', 'Sent', 'Drafts', 'Trash', 'Junk', ]

# Execute addition SQL commands after successfully created new users.
#
# Available placeholders:
#   - $user_idnr: value of dbmail_users.user_idnr
#   - $mail:     replaced by email address of newly created user
#   - $username: replaced by username part of email address
#   - $domain:   replaced by domain part of email address
#
# For example:
#
#   DBMAIL_SQL_FOR_NEWLY_CREATED_USER = [
#       """INSERT INTO dbmail_sievescripts (owner_idnr, name, script, active)
#               VALUES (
#                       $user_idnr,
#                       'Move SPAM to Junk folder',
#                       'require ["fileinto"]; if header :is "X-Spam-Flag" "YES" {fileinto "Junk"; stop;}',
#                       1)
#       """,
#   ]
#
DBMAIL_SQL_FOR_NEWLY_CREATED_USER = []

###################################
# Minor settings. You do not need to change them.
#
# List how many items in one page. e.g. domain list, user list.
PAGE_SIZE_LIMIT = 50

# Path to the logo image.
# Please copy your logo image to 'static/' folder, then put the image file name
# in BRAND_LOGO.  e.g.: 'logo.png' (will load file 'static/logo.png').
BRAND_LOGO = ''

# Product name, short description.
BRAND_NAME = 'iRedAdmin-Pro'
BRAND_DESC = 'iRedMail Admin Panel'
