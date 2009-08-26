#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

# URL schema:
#
# accountType:    domain, admin, user, maillist, alias
# account:        example.com, postmaster@example.com,
#                 www@example.com, list01@example.com,
#                 alias01@example.com
#
# * Create new accounts:
#   - /create/{accountType}
#
# * Delete accounts:
#   - /delete/{accountType}/{account}
#
# * List all accounts:
#   - /domains
#   - /admins
#
# * Show a search form for user to choose domain.
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
#   - /profile/{accountType}/{account}
#

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

        # Preferences.
        '/preferences',                     'controllers.ldap.preferences.Preferences',

        # Domain related.
        '/domains',                         'controllers.ldap.domain.list',
        '/profile/domain/(general)/(.*\..*)',         'controllers.ldap.domain.profile',
        '/profile/domain/(services)/(.*\..*)',         'controllers.ldap.domain.profile',
        '/profile/domain/(admins)/(.*\..*)',         'controllers.ldap.domain.profile',
        '/profile/domain/(quotas)/(.*\..*)',         'controllers.ldap.domain.profile',
        '/profile/domain/(backupmx)/(.*\..*)',         'controllers.ldap.domain.profile',
        '/profile/domain/(bcc)/(.*\..*)',         'controllers.ldap.domain.profile',
        '/profile/domain/(advanced)/(.*\..*)',         'controllers.ldap.domain.profile',
        '/profile/domain/(.*\..*)',         'controllers.ldap.domain.profile',
        '/create/domain',                   'controllers.ldap.domain.create',
        '/delete/domain',                   'controllers.ldap.domain.delete',

        # Admin related.
        '/admins',                          'controllers.ldap.admin.list',
        '/profile/admin/(.*@.*\..*)',       'controllers.ldap.admin.profile',
        '/create/admin',                    'controllers.ldap.admin.create',
        '/delete/admin',                    'controllers.ldap.admin.delete',

        # User related.
        # /domain.ltd/users
        '/users',                           'controllers.ldap.user.list',
        '/users/(.*\..*)',                  'controllers.ldap.user.list',
        '/profile/user/(general)/(.*@.*\..*)',        'controllers.ldap.user.profile',
        '/profile/user/(shadow)/(.*@.*\..*)',        'controllers.ldap.user.profile',
        '/profile/user/(groups)/(.*@.*\..*)',        'controllers.ldap.user.profile',
        '/profile/user/(services)/(.*@.*\..*)',        'controllers.ldap.user.profile',
        '/profile/user/(forwarding)/(.*@.*\..*)',        'controllers.ldap.user.profile',
        '/profile/user/(bcc)/(.*@.*\..*)',        'controllers.ldap.user.profile',
        '/profile/user/(password)/(.*@.*\..*)',        'controllers.ldap.user.profile',
        '/profile/user/(advanced)/(.*@.*\..*)',        'controllers.ldap.user.profile',
        '/profile/user/(.*@.*\..*)',        'controllers.ldap.user.profile',
        '/create/user/(.*\..*)',            'controllers.ldap.user.create',
        '/create/user',                     'controllers.ldap.user.create',
        '/delete/user',                     'controllers.ldap.user.delete',
        )
