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
# Admin related.
# ---------------------------------------------------------
ADMIN_ATTRS_ALL = ['accountStatus', 'cn', 'preferredLanguage', 'createTimestamp', ]

# ---------------------------------------------------------
# Domain related.
# ---------------------------------------------------------
DOMAIN_FILTER = '(objectClass=mailDomain)'

# Default groups which will be created while create a new domain.
# WARNING: Don't use unicode str here.
DEFAULT_GROUPS = ['Users', 'Groups', 'Aliases', 'Externals',]

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

DOMAIN_PROFILE_TYPE = [
        'general', 'admins', 'services', 'bcc', 'quotas',
        'backupmx', 'advanced',
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
        'mail', 'cn', 'accountStatus', 'mailQuota', 'employeeNumber',
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

USER_PROFILE_TYPE = [
        'general', 'shadow', 'groups', 'services', 'forwarding',
        'bcc', 'password', 'advanced',
        ]
