# Author: Zhang Huangbin <zhb@iredmail.org>

from libs.iredutils import reEmail, reDomain

urls = [
    # Make url ending with or without '/' going to the same class.
    '/(.*)/',                           'controllers.utils.redirect',

    # used to display jpegPhoto.
    '/img/(.*)',                        'controllers.utils.img',

    '/',                                'controllers.mysql.basic.Login',
    '/login',                           'controllers.mysql.basic.Login',
    '/logout',                          'controllers.mysql.basic.Logout',
    '/dashboard',                       'controllers.mysql.basic.Dashboard',
    '/dashboard/(checknew)',            'controllers.mysql.basic.Dashboard',

    # Search.
    '/search',                          'controllers.mysql.basic.Search',

    # Perform some operations from search page.
    '/action/(user|alias)',   'controllers.mysql.basic.OperationsFromSearchPage',

    # Domain related.
    '/domains',                         'controllers.mysql.domain.List',
    '/domains/page/(\d+)',              'controllers.mysql.domain.List',
    '/profile/domain/(general|aliases|relay|bcc|catchall|throttle|advanced)/(%s$)' % reDomain,  'controllers.mysql.domain.Profile',
    '/profile/domain/(%s)' % reDomain,  'controllers.mysql.domain.Profile',
    '/create/domain',                   'controllers.mysql.domain.Create',

    # Admin related.
    '/admins',                          'controllers.mysql.admin.List',
    '/admins/page/(\d+)',               'controllers.mysql.admin.List',
    '/profile/admin/(general|password)/(%s$)' % reEmail,     'controllers.mysql.admin.Profile',
    '/create/admin',                    'controllers.mysql.admin.Create',

    # User related.
    # /domain.ltd/users
    '/users',                           'controllers.mysql.user.List',
    '/users/(%s$)' % reDomain,           'controllers.mysql.user.List',
    '/users/(%s)/page/(\d+)' % reDomain, 'controllers.mysql.user.List',
    # Create user.
    '/create/user/(%s$)' % reDomain,     'controllers.mysql.user.Create',
    '/create/user',                     'controllers.mysql.user.Create',
    # Profile pages.
    '/profile/user/(general|forwarding|bcc|relay|wblist|password|throttle|advanced)/(%s$)' % reEmail,      'controllers.mysql.user.Profile',

    # Import accouts.
    '/import/user',                     'controllers.mysql.user.ImportUser',

    # Alias related.
    '/aliases',                         'controllers.mysql.alias.List',
    '/aliases/(%s$)' % reDomain,                         'controllers.mysql.alias.List',
    '/aliases/(%s)/page/(\d+)' % reDomain,              'controllers.mysql.alias.List',
    '/profile/alias/(general|members)/(%s$)' % reEmail,  'controllers.mysql.alias.Profile',
    '/create/alias/(%s$)' % reDomain,                    'controllers.mysql.alias.Create',
    '/create/alias',                                    'controllers.mysql.alias.Create',
]
