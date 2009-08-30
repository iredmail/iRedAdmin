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

# Regular expressions.
re_email = '[\w\-][\w\-\.]+@[\w\-][\w\-\.]+[a-zA-Z]{1,4}'
re_domain = '[\w\-][\w\-\.]+[a-zA-Z]{1,4}'

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
        '/delete/domain',                               'controllers.ldap.domain.delete',

        # Admin related.
        '/admins',                          'controllers.ldap.admin.list',
        '/profile/admin/(%s)' % re_email,   'controllers.ldap.admin.profile',
        '/create/admin',                    'controllers.ldap.admin.create',
        '/delete/admin',                    'controllers.ldap.admin.delete',

        # User related.
        # /domain.ltd/users
        '/users',                                       'controllers.ldap.user.list',
        '/users/(%s)' % re_domain,                      'controllers.ldap.user.list',
        '/profile/user/(general)/(%s)' % re_email,      'controllers.ldap.user.profile',
        '/profile/user/(shadow)/(%s)' % re_email,       'controllers.ldap.user.profile',
        '/profile/user/(groups)/(%s)' % re_email,       'controllers.ldap.user.profile',
        '/profile/user/(services)/(%s)' % re_email,     'controllers.ldap.user.profile',
        '/profile/user/(forwarding)/(%s)' % re_email,   'controllers.ldap.user.profile',
        '/profile/user/(bcc)/(%s)' % re_email,          'controllers.ldap.user.profile',
        '/profile/user/(password)/(%s)' % re_email,     'controllers.ldap.user.profile',
        '/profile/user/(advanced)/(%s)' % re_email,     'controllers.ldap.user.profile',
        '/profile/user/(%s)' % re_email,                'controllers.ldap.user.profile',
        '/create/user/(%s)' % re_domain,                'controllers.ldap.user.create',
        '/create/user',                                 'controllers.ldap.user.create',
        '/delete/user',                                 'controllers.ldap.user.delete',

        # Group related.
        '/maillists',                           'controllers.ldap.maillist.list',
        '/maillists/(%s)' % re_domain,          'controllers.ldap.maillist.list',
        '/profile/maillist/(%s)' % re_email,    'controllers.ldap.maillist.profile',
        '/create/maillist/(%s)' % re_domain,    'controllers.ldap.maillist.create',
        '/create/maillist',                     'controllers.ldap.maillist.create',
        '/delete/maillist',                     'controllers.ldap.maillist.delete',

        # Alias related.
        '/aliases',                         'controllers.ldap.alias.list',
        '/aliases/(%s)' % re_domain,        'controllers.ldap.alias.list',
        '/profile/alias/(%s)' % re_email,   'controllers.ldap.alias.profile',
        '/create/alias/(%s)' % re_domain,   'controllers.ldap.alias.create',
        '/create/alias',                    'controllers.ldap.alias.create',
        '/delete/alias',                    'controllers.ldap.alias.delete',
        )
