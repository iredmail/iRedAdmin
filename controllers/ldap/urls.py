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
        '/img/(.*)',                        'controllers.ldap.utils.img',

        '/',                                'controllers.ldap.core.login',
        '/login',                           'controllers.ldap.core.login',
        '/logout',                          'controllers.ldap.core.logout',
        '/dashboard',                       'controllers.ldap.core.dashboard',

        # Preferences.
        '/preferences',                     'controllers.ldap.preferences.Preferences',

        # Domain related.
        '/domains',                         'controllers.ldap.domain.list',
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
        '/profile/user/(.*@.*\..*)',        'controllers.ldap.user.profile',
        '/create/user/(.*\..*)',            'controllers.ldap.user.create',
        '/create/user',                     'controllers.ldap.user.create',
        '/delete/user',                     'controllers.ldap.user.delete',
        )
