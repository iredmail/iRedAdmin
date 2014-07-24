# Author: Zhang Huangbin <zhb@iredmail.org>

#
# WARNING
#
# Please place all your settings in settings.py to override settings below, so
# that you can simply copy settings.py after upgrading iRedAdmin.
#

# Debug iRedAdmin: True, False.
DEBUG = False

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

# Allow to store password in plain text.
# It will show a HTML checkbox to allow admin to store newly created user
# password or reset password in plain text. If not checked, password
# will be stored as encrypted.
# See LDAP_DEFAULT_PASSWD_SCHEME and SQL_DEFAULT_PASSWD_SCHEME below.
STORE_PASSWORD_IN_PLAIN_TEXT_TEXT = False

# Print PERMISSION_DENIED related programming info to stdout or web server
# log file. e.g. Apache log file.
LOG_PERMISSION_DENIED = False

# Redirect to "Domains and Accounts" page instead of Dashboard.
REDIRECT_TO_DOMAIN_LIST_AFTER_LOGIN = False

###################################
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


#######################################
# OpenLDAP backend related settings.
#

# LDAP connection trace level. Must be an integer.
LDAP_CONN_TRACE_LEVEL = 0

# Default password scheme: SSHA, SHA, PLAIN.
# Must be a string. SSHA is recommended.
# To store passwords in plain text, please change below setting to 'PLAIN',
# no addition changes are required in iredmail, dovecot will detect password
# scheme automatically.
LDAP_DEFAULT_PASSWD_SCHEME = 'SSHA'

#######################################
# MySQL/PostgreSQL backends related settings. Note: Not applicable for DBMail.
#

# Default password scheme: MD5, SSHA, SSHA512, PLAIN-MD5, PLAIN.
#
# Passwords of new accounts (admin, user) will be crypted by specified scheme.
#
# - MD5: MD5 based salted password hash.
#       Example: '$1$ozdpg0V0$0fb643pVsPtHVPX8mCZYW/'.
#
# - SSHA: {SSHA} is RFC 2307 password scheme which use the SHA1 secure hash
#       algorithm. The {SSHA} is the seeded varient. {SSHA} is recommended
#       over other RFC 2307 schemes.
#       Example: {SSHA}bfxqKqOOKODJw/bGqMo54f9Q/iOvQoftOQrqWA==
#
# - SSHA512: {SSHA512} is salted SHA512 which uses the SHA2 secure hash
#       algorithm, SSHA512 is better than SSHA.
#       Example: {SSHA512}FxgXDhBVYmTqoboW+ibyyzPv/wGG7y4VJtuHWrx+wfqrs/lIH2Qxn2eA0jygXtBhMvRi7GNFmL++6aAZ0kXpcy1fxag=
#       Note: SSHA512 support requires Dovecot-2.0 (and later) and Python-2.5
#             (and later).
#
# - PLAIN-MD5: MD5 based password without salt.
#       Example: 900150983cd24fb0d6963f7d28e17f72.
#
# - PLAIN: Plain text.
#
# Reference:
#   - For dovecot-1.1.x, 1.2.x: http://wiki.dovecot.org/Authentication/PasswordSchemes
#   - For dovecot-2.x: http://wiki2.dovecot.org/Authentication/PasswordSchemes
SQL_DEFAULT_PASSWD_SCHEME = 'MD5'

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
# Policyd related settings.
#

# Priority of Policyd policies, includes throttling, greylist opt-in, etc.
POLICY_PRIORITY_OF_DOMAIN = 10
POLICY_PRIORITY_OF_USER = 20

# If you turn off greylisting in Policyd config file (policyd.conf), please
# turn below setting to False.
POLICY_GREYLISTED_BY_DEFAULT = True

###################################
# Minor settings. You do not need to change them.
#
# List how many items in one page. e.g. domain list, user list.
PAGE_SIZE_LIMIT = 50

# Import local settings.
try:
    from libs.settings_local import *
except Exception:
    pass
