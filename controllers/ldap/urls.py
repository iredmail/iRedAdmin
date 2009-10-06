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

# URL schema:
#
# accountType:    domain, admin, user, maillist, alias
# account:        example.com, postmaster@example.com,
#                 www@example.com, list01@example.com,
#                 alias01@example.com
#
# * Create new domain:
#   - /create/{accountType}
#
# * Create new account:
#   - /create/{accountType}[/domain]
#
# * List all accounts:
#   - /domains
#   - /admins
#   - /users
#   - /maillists
#   - /aliases
#
# * List all accounts under single domain.
#   - /users/{domain}
#   - /maillists/{domain}
#   - /aliases/{domain}
#
# * View & Update account profile:
#   - /profile/{accountType}/{profile_type}/{account}
#

# Regular expressions.
re_email = r'[\w\-][\w\-\.]*@[\w\-][\w\-\.]+[a-zA-Z]{1,4}'
re_domain = '[\w\-][\w\-\.]*[a-zA-Z]{1,4}'

urls = (
        # Make url ending with or without '/' going to the same class.
        '/(.*)/',                           'controllers.ldap.base.redirect',

        # used to display jpegPhoto.
        '/img/(.*)',                        'controllers.utils.img',

        '/',                                'controllers.ldap.basic.login',
        '/login',                           'controllers.ldap.basic.login',
        '/logout',                          'controllers.ldap.basic.logout',
        '/dashboard',                       'controllers.ldap.basic.dashboard',
        '/checknew',                        'controllers.ldap.basic.checknew',

        # Domain related.
        '/domains',                                     'controllers.ldap.domain.list',
        '/profile/domain/(general)/(%s)' % re_domain,   'controllers.ldap.domain.profile',
        '/profile/domain/(services)/(%s)' % re_domain,  'controllers.ldap.domain.profile',
        '/profile/domain/(admins)/(%s)' % re_domain,    'controllers.ldap.domain.profile',
        '/profile/domain/(quotas)/(%s)' % re_domain,    'controllers.ldap.domain.profile',
        '/profile/domain/(backupmx)/(%s)' % re_domain,  'controllers.ldap.domain.profile',
        '/profile/domain/(bcc)/(%s)' % re_domain,       'controllers.ldap.domain.profile',
        #'/profile/domain/(advanced)/(%s)' % re_domain,  'controllers.ldap.domain.profile',
        '/profile/domain/(%s)' % re_domain,             'controllers.ldap.domain.profile',
        '/create/domain',                               'controllers.ldap.domain.create',

        # Admin related.
        '/admins',                                      'controllers.ldap.admin.list',
        '/profile/admin/(general)/(%s)' % re_email,     'controllers.ldap.admin.profile',
        '/profile/admin/(password)/(%s)' % re_email,    'controllers.ldap.admin.profile',
        '/profile/admin/(domains)/(%s)' % re_email,     'controllers.ldap.admin.profile',
        '/create/admin',                                'controllers.ldap.admin.create',

        # User related.
        # /domain.ltd/users
        '/users',                                       'controllers.ldap.user.list',
        '/users/(%s)' % re_domain,                      'controllers.ldap.user.list',
        '/profile/user/(general)/(%s)' % re_email,      'controllers.ldap.user.profile',
        '/profile/user/(shadow)/(%s)' % re_email,       'controllers.ldap.user.profile',
        '/profile/user/(members)/(%s)' % re_email,       'controllers.ldap.user.profile',
        '/profile/user/(services)/(%s)' % re_email,     'controllers.ldap.user.profile',
        '/profile/user/(forwarding)/(%s)' % re_email,   'controllers.ldap.user.profile',
        '/profile/user/(bcc)/(%s)' % re_email,          'controllers.ldap.user.profile',
        '/profile/user/(password)/(%s)' % re_email,     'controllers.ldap.user.profile',
        '/profile/user/(advanced)/(%s)' % re_email,     'controllers.ldap.user.profile',
        '/profile/user/(%s)' % re_email,                'controllers.ldap.user.profile',
        '/create/user/(%s)' % re_domain,                'controllers.ldap.user.create',
        '/create/user',                                 'controllers.ldap.user.create',

        )
