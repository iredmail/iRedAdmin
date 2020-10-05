# Author: Zhang Huangbin <zhb@iredmail.org>

# ---------------------------------------------------------
# Values.
# ---------------------------------------------------------
# All account types which can be converted to ldap dn.
#   - `maillist` is old style mailing list, should be converted to LDAP group.
#   - `ml` is mlmmj mailing list
ACCOUNT_TYPES_ALL = (
    'domain', 'catchall', 'admin', 'user', 'alias',
    'maillist', 'maillistExternal', 'ml',
)
ACCOUNT_TYPES_EMAIL = (
    'admin', 'user', 'alias',
    'maillist', 'maillistExternal', 'ml',
)
ACCOUNT_TYPES_DOMAIN = ('domain', 'catchall')

# Default groups which will be created while create a new domain.
# WARNING: Don't use unicode string here.
GROUP_USERS = 'Users'
GROUP_GROUPS = 'Groups'
GROUP_ALIASES = 'Aliases'
GROUP_EXTERNALS = 'Externals'
DEFAULT_GROUPS = (GROUP_USERS, GROUP_GROUPS, GROUP_ALIASES, GROUP_EXTERNALS)

DN_BETWEEN_USER_AND_DOMAIN = DN_BETWEEN_CATCHALL_AND_DOMAIN = 'ou=%s,' % (GROUP_USERS)
DN_BETWEEN_GROUP_AND_DOMAIN = 'ou=%s,' % (GROUP_GROUPS)
DN_BETWEEN_GROUP_EXTERNAL_AND_DOMAIN = 'ou=%s,' % (GROUP_EXTERNALS)
DN_BETWEEN_ALIAS_AND_DOMAIN = 'ou=%s,' % (GROUP_ALIASES)

# RDN of accounts: mail, cn, uid. Default is 'mail'.
# Note: Although you can use other attr as RDN, but all mail user/list/alias
#       must have 'mail' attribute.
RDN_USER = 'mail'
RDN_ML = RDN_MAILLIST = RDN_ALIAS = RDN_ADMIN = RDN_CATCHALL = 'mail'
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
ADMIN_SEARCH_ATTRS = (
    'mail', 'accountStatus', 'cn', 'preferredLanguage',
    'domainGlobalAdmin',
    'enabledService', 'disabledService',
    'accountSetting',
    'objectClass',
)
ADMIN_ATTRS_ALL = tuple(list(ADMIN_SEARCH_ATTRS) + ['sn', 'givenName'])

# ---------------------------------------------------------
# Domain related.
# ---------------------------------------------------------
DOMAIN_FILTER = '(objectClass=mailDomain)'
# All available services.
DOMAIN_ENABLED_SERVICE = (
    'mail', 'domainalias',
    'senderbcc', 'recipientbcc',
    'self-service',
)

# Services for newly added mail domain.
DOMAIN_ENABLED_SERVICE_FOR_NEW_DOMAIN = ('mail', )

# Services available in 'Service Control' page.
DOMAIN_SERVICE_UNDER_CONTROL = (
    'mail', 'domainalias',
    'senderbcc', 'recipientbcc',
    'self-service',
)

DOMAIN_SEARCH_ATTRS = (
    # Attributes used in domain list page.
    'domainName', 'domainPendingAliasName', 'domainAliasName',
    'domainAdmin',
    'cn', 'mtaTransport', 'accountStatus', 'domainBackupMX',
    'domainCurrentQuotaSize',
    'domainCurrentUserNumber',
    'domainCurrentListNumber',
    'domainCurrentAliasNumber',
    'accountSetting',
)

DOMAIN_ATTRS_ALL = (
    # Normal attributes.
    'domainName', 'domainPendingAliasName', 'domainAliasName',
    'cn', 'description', 'accountStatus', 'domainBackupMX',
    'domainAdmin', 'mtaTransport', 'enabledService',
    'domainRecipientBccAddress', 'domainSenderBccAddress',
    'senderRelayHost', 'disclaimer',
    'domainCurrentQuotaSize',
    'domainCurrentUserNumber',
    'domainCurrentListNumber',
    'domainCurrentAliasNumber',
    'accountSetting',
)

# ---------------------------------------------------------
# User related.
# ---------------------------------------------------------
USER_FILTER = '(objectClass=mailUser)'
USER_ATTR_PASSWORD = 'userPassword'

# Services for normal user. used while adding a new mail user.
USER_SERVICES_INTERNAL = (
    'internal', 'doveadm', 'lib-storage',
    'indexer-worker', 'dsync', 'quota-status',
)

USER_SERVICES_OF_NORMAL_USER = tuple(list(USER_SERVICES_INTERNAL) + [
    'mail',
    'smtp', 'smtpsecured', 'smtptls',
    'pop3', 'pop3secured', 'pop3tls',
    'imap', 'imapsecured', 'imaptls',
    'managesieve', 'managesievesecured', 'managesievetls',
    # For Dovecot-1.x
    'sieve', 'sievesecured', 'sievetls',
    'deliver', 'lda', 'lmtp',
    'recipientbcc', 'senderbcc',
    'forward', 'shadowaddress',
    'displayedInGlobalAddressBook',
    'sogo',
])

# All available services for a mail user account.
USER_SERVICES_ALL = tuple(list(USER_SERVICES_OF_NORMAL_USER) + ['domainadmin'])

# All attributes needed in user list page.
USER_SEARCH_ATTRS = (
    'mail', 'cn', 'uid', 'accountStatus', 'mailQuota',
    'employeeNumber', 'title', 'senderRelayHost',
    'shadowAddress', 'mailForwardingAddress', 'memberOfGroup',
    'enabledService', 'disabledService',
    'domainGlobalAdmin',    # Global admin
    'shadowLastChange',     # Password last change, it's number of days since
                            # epoch date (1970-01-01).
)

USER_ATTRS_ALL = tuple(list(USER_SEARCH_ATTRS) + [
    'sn', 'givenName', 'uid',
    'mobile', 'telephoneNumber', 'preferredLanguage', 'memberOfGroup',
    'userRecipientBccAddress', 'userSenderBccAddress',
    'mailForwardingAddress',
    # Transport and relayhost
    'mtaTransport',
    # Maildir path
    'storageBaseDirectory', 'mailMessageStore', 'homeDirectory',
    'accountSetting',
    'allowNets',
    'street',
    'postalCode',
    'postalAddress',
])

# ---------------------------------------------------------
# Mailing list related.
# ---------------------------------------------------------
# Default groups which will be created while create a new domain.
MAILLIST_ENABLED_SERVICE = ('mail', 'deliver')

MAILLIST_SEARCH_ATTRS = (
    # Required attributes.
    'mail', 'shadowAddress',
    'accountStatus',
    'cn',
    'accessPolicy',
    'enabledService',
    'mtaTransport',
)

MAILLIST_ATTRS_ALL = (
    # Required attributes.
    'mail', 'shadowAddress',
    'accountStatus',
    'cn',
    'enabledService',
    'accessPolicy', 'listAllowedUser',
)

# ---------------------------------------------------------
# Alias related.
# ---------------------------------------------------------
ALIAS_ENABLED_SERVICE = ('mail', 'deliver')

ALIAS_SEARCH_ATTRS = (
    'mail', 'shadowAddress',
    'accountStatus', 'cn',
    'enabledService', 'mailForwardingAddress',
)

ALIAS_ATTRS_ALL = ALIAS_SEARCH_ATTRS
