# Author: Zhang Huangbin <zhb@iredmail.org>

from libs.iredutils import reEmail, reDomain

urls = [
    # Make url ending with or without '/' going to the same class.
    '/(.*)/',                           'controllers.utils.redirect',

    # used to display jpegPhoto.
    '/img/(.*)',                        'controllers.utils.img',

    '/',                                'controllers.ldap.basic.Login',
    '/login',                           'controllers.ldap.basic.Login',
    '/logout',                          'controllers.ldap.basic.Logout',
    '/dashboard',                       'controllers.ldap.basic.Dashboard',
    '/dashboard/(checknew)',              'controllers.ldap.basic.Dashboard',

    # Search.
    '/search',                                  'controllers.ldap.basic.Search',

    # Perform some operations from search page.
    '/action/(domain|admin|user|maillist|alias)', 'controllers.ldap.basic.OperationsFromSearchPage',

    # Export LDIF data.
    '/export/ldif/(domain|catchall)/(%s$)' % reDomain,           'controllers.ldap.basic.ExportLdif',
    '/export/ldif/(admin|user|maillist|alias)/(%s$)' % reEmail,  'controllers.ldap.basic.ExportLdif',

    # Domain related.
    '/domains',                                     'controllers.ldap.domain.List',
    '/domains/page/(\d+)',                          'controllers.ldap.domain.List',
    '/profile/domain/(general|aliases|relay|bcc|catchall|throttle|advanced)/(%s$)' % reDomain,  'controllers.ldap.domain.Profile',
    '/profile/domain/(%s)' % reDomain,             'controllers.ldap.domain.Profile',
    '/create/domain',                               'controllers.ldap.domain.Create',

    # Admin related.
    '/admins',                                      'controllers.ldap.admin.List',
    '/admins/page/(\d+)',                           'controllers.ldap.admin.List',
    '/profile/admin/(general|password)/(%s$)' % reEmail,     'controllers.ldap.admin.Profile',
    '/create/admin',                                'controllers.ldap.admin.Create',

    #########################
    # User related
    #
    # List users, delete users under same domain.
    '/users',                                       'controllers.ldap.user.List',
    '/users/(%s$)' % reDomain,                       'controllers.ldap.user.List',
    '/users/(%s)/page/(\d+)' % reDomain,            'controllers.ldap.user.List',
    # Create user.
    '/create/user/(%s$)' % reDomain,                'controllers.ldap.user.Create',
    '/create/user',                               'controllers.ldap.user.Create',
    # Profile pages.
    '/profile/user/(general|members|forwarding|aliases|wblist|password|throttle|advanced)/(%s$)' % reEmail,      'controllers.ldap.user.Profile',

    # Import accouts.
    '/import/user',                               'controllers.ldap.user.Import',
    '/import/user/(%s$)' % reDomain,                'controllers.ldap.user.Import',
    '/import/alias',                               'controllers.ldap.alias.Import',

    ####################
    # Mail list related
    #
    # List accounts
    '/maillists',                                   'controllers.ldap.maillist.List',
    '/maillists/(%s$)' % reDomain,                    'controllers.ldap.maillist.List',
    '/maillists/(%s)/page/(\d+)' % reDomain,         'controllers.ldap.maillist.List',

    # General profile.
    '/profile/maillist/(general)/(%s$)' % reEmail,    'controllers.ldap.maillist.Profile',
    '/profile/maillist/members/(%s$)' % reEmail,      'controllers.ldap.maillist.Members',
    '/profile/maillist/moderators/(%s$)' % reEmail,               'controllers.ldap.maillist.Moderators',
    '/create/maillist/(%s$)' % reDomain,            'controllers.ldap.maillist.Create',
    '/create/maillist',                           'controllers.ldap.maillist.Create',

    # Alias related.
    '/aliases',                                         'controllers.ldap.alias.List',
    '/aliases/(%s$)' % reDomain,                         'controllers.ldap.alias.List',
    '/aliases/(%s)/page/(\d+)' % reDomain,              'controllers.ldap.alias.List',
    '/profile/alias/(general)/(%s$)' % reEmail,          'controllers.ldap.alias.Profile',
    '/create/alias/(%s$)' % reDomain,                    'controllers.ldap.alias.Create',
    '/create/alias',                                    'controllers.ldap.alias.Create',
]
