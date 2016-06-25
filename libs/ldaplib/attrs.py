# Author: Zhang Huangbin <zhb@iredmail.org>

# ---------------------------------------------------------
# Values.
# ---------------------------------------------------------
ACCOUNT_STATUS_ACTIVE = 'active'
ACCOUNT_STATUS_DISABLED = 'disabled'
ACCOUNT_STATUSES = [ACCOUNT_STATUS_ACTIVE, ACCOUNT_STATUS_DISABLED, ]

# All account types which can be converted to ldap dn.
ACCOUNT_TYPES_ALL = ['domain', 'catchall', 'admin', 'user', 'maillist', 'maillistExternal', 'alias', ]
ACCOUNT_TYPES_EMAIL = ['admin', 'user', 'maillist', 'maillistExternal', 'alias', ]
ACCOUNT_TYPES_DOMAIN = ['domain', 'catchall', ]

# Default groups which will be created while create a new domain.
# WARNING: Don't use unicode string here.
GROUP_USERS = 'Users'
GROUP_GROUPS = 'Groups'
GROUP_ALIASES = 'Aliases'
GROUP_EXTERNALS = 'Externals'
DEFAULT_GROUPS = [GROUP_USERS, GROUP_GROUPS, GROUP_ALIASES, GROUP_EXTERNALS, ]

#
DN_BETWEEN_USER_AND_DOMAIN = DN_BETWEEN_CATCHALL_AND_DOMAIN = 'ou=%s,' % (GROUP_USERS, )
DN_BETWEEN_MAILLIST_AND_DOMAIN = 'ou=%s,' % (GROUP_GROUPS, )
DN_BETWEEN_ALIAS_AND_DOMAIN = 'ou=%s,' % (GROUP_ALIASES, )
DN_BETWEEN_MAILLIST_EXTERNAL_AND_DOMAIN = 'ou=%s,' % (GROUP_EXTERNALS, )

# RDN of accounts. Default is 'mail'.
# Note: Although you can use other attr as RDN, but all mail user/list/alias
#       must have 'mail' attribute.
RDN_USER = 'mail'       # Supports: mail, cn, uid.
RDN_MAILLIST = RDN_ALIAS = RDN_ADMIN = RDN_CATCHALL = 'mail'
RDN_MAILLIST_EXTERNAL = 'memberOfGroup'
RDN_DOMAIN = 'domainName'

# ---------------------------------------------------------
# Attributes.
# ---------------------------------------------------------
ATTR_GLOBAL_ADMIN = 'domainGlobalAdmin'
ATTR_DOMAIN_CURRENT_QUOTA_SIZE = 'domainCurrentQuotaSize'

# ---------------------------------------------------------
# Admin related.
# ---------------------------------------------------------
ADMIN_SEARCH_ATTRS = ['mail', 'accountStatus', 'cn', 'preferredLanguage',
                      'domainGlobalAdmin', 'enabledService',
                      'objectClass']
ADMIN_ATTRS_ALL = ADMIN_SEARCH_ATTRS + ['sn', 'givenName']

# ---------------------------------------------------------
# Domain related.
# ---------------------------------------------------------
DOMAIN_FILTER = '(objectClass=mailDomain)'
# All availabe services.
DOMAIN_ENABLED_SERVICE = ('mail', 'domainalias', 'senderbcc', 'recipientbcc',)

# Services availabel in 'Service Control' page.
DOMAIN_SERVICE_UNDER_CONTROL = ['mail', 'domainalias', 'senderbcc', 'recipientbcc', ]

DOMAIN_SEARCH_ATTRS = [
    # Attributes used in domain list page.
    'domainName', 'domainAliasName', 'domainAdmin',
    'cn', 'mtaTransport', 'accountStatus',
    'domainCurrentQuotaSize',
    'domainCurrentUserNumber',
    'domainCurrentListNumber',
    'domainCurrentAliasNumber',
    'accountSetting',
]

DOMAIN_ATTRS_ALL = [
    # Normal attributes.
    'domainName', 'domainAliasName', 'cn', 'description', 'accountStatus', 'domainBackupMX',
    'domainAdmin', 'mtaTransport', 'enabledService',
    'domainRecipientBccAddress', 'domainSenderBccAddress',
    'disclaimer',
    'domainCurrentQuotaSize',
    'domainCurrentUserNumber',
    'domainCurrentListNumber',
    'domainCurrentAliasNumber',
    'accountSetting',
]

VALUES_DOMAIN_BACKUPMX = ['yes', 'no']

# ---------------------------------------------------------
# User related.
# ---------------------------------------------------------
USER_FILTER = '(objectClass=mailUser)'
USER_ATTR_PASSWORD = 'userPassword'
USER_SEARCH_ATTRS = [
    # Required attributes.
    'mail', 'cn', 'accountStatus', 'mailQuota',
    'employeeNumber', 'title', 'shadowAddress', 'memberOfGroup',
    'storageBaseDirectory', 'mailMessageStore',
]

USER_ATTRS_ALL = [
    'mail', 'cn', 'accountStatus', 'mailQuota', 'jpegPhoto',
    'sn', 'givenName',
    'enabledService', 'memberOfGroup', 'employeeNumber', 'preferredLanguage',
    'telephoneNumber', 'userRecipientBccAddress', 'userSenderBccAddress',
    'mailForwardingAddress', 'mtaTransport',
    'storageBaseDirectory', 'mailMessageStore', 'homeDirectory',    # Maildir
    'mobile', 'title', 'shadowAddress',
    'shadowLastChange',     # Date of last password change, it's a integer.
    'domainGlobalAdmin',    # Global admin
]
