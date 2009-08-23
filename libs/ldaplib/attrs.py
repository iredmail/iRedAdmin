#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

# ---------------------------------------------------------------------------
# Default structure in iRedMail schema.
#   dc=example,dc=com                       # LDAP_SUFFIX
#     |- cn=vmai
#     |- cn=vmailadmin
#     |- o=domainAdmins                     # Container used to store domain admin accounts.
#         |- mail=admin@domain.ltd          # Domain admin.
#         |- mail=postmaster@domain2.ltd
#     |- o=domains
#         |- domainName=hello.com
#         |- domainName=world.com           # Virtual domain.
#               |- ou=Users
#                   |- mail=user1@world.com     # Virtual mail user.
#                   |- mail=user2@world.com
#                   |- mail=user3@world.com
# ---------------------------------------------------------

# ---------------------------------------------------------
# Values.
# ---------------------------------------------------------
VALUES_ACCOUNT_STATUS = ['active', 'disabled']

# ---------------------------------------------------------
# Domain admin related.
# ---------------------------------------------------------
DOMAIN_RDN = 'domainName'
ATTR_GLOBAL_ADMIN = 'domainGlobalAdmin'
DOMAINADMIN_SEARCH_FILTER = '(objectClass=mailAdmin)'
DOMAINADMIN_SEARCH_ATTRS = ['mail', 'accountStatus', 'domainGlobalAdmin', 'cn', 'enabledService']

# ---------------------------------------------------------
# Domain related.
# ---------------------------------------------------------
DOMAIN_FILTER = '(objectClass=mailDomain)'

# Default groups which will be created while create a new domain.
DEFAULT_GROUPS = ['Users', 'Groups', 'Aliases',]    # Don't list unicode str here.

DOMAIN_SEARCH_ATTRS = [
        # Normal attributes.
        'domainName', 'accountStatus', 'domainCurrentUserNumber',
        # Internal/System attributes.
        'createTimestamp',
        ]

DOMAIN_ATTRS_ALL = [
        # Normal attributes.
        'domainName', 'cn', 'description', 'accountStatus', 'domainBackupMX',
        'domainAdmin', 'mtaTransport',
        # Internal/System attributes.
        'createTimestamp',
        ]

VALUES_DOMAIN_BACKUPMX = ['yes', 'no']

# ---------------------------------------------------------
# User related.
# ---------------------------------------------------------
USER_RDN = 'mail'
USER_FILTER = '(objectClass=mailUser)'
USER_ATTR_PASSWORD = 'userPassword'

USER_SEARCH_ATTRS = [
        # Required attributes.
        'mail', 'cn', 'accountStatus', 'mailQuota', 'jpegPhoto',
        'createTimestamp',                      # Internal/System attributes.
        ]

USER_ATTRS_ALL = [
        # Required attributes.
        'mail', 'cn', 'accountStatus', 'mailQuota', 'jpegPhoto',
        'enabledService', 'memberOfGroup', 'employeeNumber',
        'telephoneNumber', 'userRecipientBccAddress', 'userSenderBccAddress',
        'mailForwardingAddress',
        'createTimestamp',                      # Internal/System attributes.
        ]
