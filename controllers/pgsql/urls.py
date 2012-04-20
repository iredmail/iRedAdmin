# Author: Zhang Huangbin <zhb@iredmail.org>

from libs.iredutils import reEmail, reDomain

urls = [
    # Make url ending with or without '/' going to the same class.
    '/(.*)/',                           'controllers.utils.redirect',

    # used to display jpegPhoto.
    '/img/(.*)',                        'controllers.utils.img',

    '/',                                'controllers.pgsql.basic.Login',
    '/login',                           'controllers.pgsql.basic.Login',
    '/logout',                          'controllers.pgsql.basic.Logout',
    '/dashboard',                       'controllers.pgsql.basic.Dashboard',
    '/dashboard/(checknew)',            'controllers.pgsql.basic.Dashboard',

    # Search.
    '/search',                          'controllers.pgsql.basic.Search',

    # Perform some operations from search page.
    '/action/(user|alias)',   'controllers.pgsql.basic.OperationsFromSearchPage',

    # Domain related.
    '/domains',                         'controllers.pgsql.domain.List',
    '/domains/page/(\d+)',              'controllers.pgsql.domain.List',
    '/profile/domain/(general|aliases|relay|bcc|catchall|throttle|advanced)/(%s$)' % reDomain,  'controllers.pgsql.domain.Profile',
    '/profile/domain/(%s)' % reDomain,  'controllers.pgsql.domain.Profile',
    '/create/domain',                   'controllers.pgsql.domain.Create',

    # Admin related.
    '/admins',                          'controllers.pgsql.admin.List',
    '/admins/page/(\d+)',               'controllers.pgsql.admin.List',
    '/profile/admin/(general|password)/(%s$)' % reEmail,     'controllers.pgsql.admin.Profile',
    '/create/admin',                    'controllers.pgsql.admin.Create',

    # User related.
    # /domain.ltd/users
    '/users',                           'controllers.pgsql.user.List',
    '/users/(%s$)' % reDomain,           'controllers.pgsql.user.List',
    '/users/(%s)/page/(\d+)' % reDomain, 'controllers.pgsql.user.List',
    # Create user.
    '/create/user/(%s$)' % reDomain,     'controllers.pgsql.user.Create',
    '/create/user',                     'controllers.pgsql.user.Create',
    # Profile pages.
    '/profile/user/(general|forwarding|bcc|relay|wblist|password|throttle|advanced)/(%s$)' % reEmail,      'controllers.pgsql.user.Profile',

    # Import accouts.
    '/import/user',                     'controllers.pgsql.user.ImportUser',

    # Alias related.
    '/aliases',                         'controllers.pgsql.alias.List',
    '/aliases/(%s$)' % reDomain,                         'controllers.pgsql.alias.List',
    '/aliases/(%s)/page/(\d+)' % reDomain,              'controllers.pgsql.alias.List',
    '/profile/alias/(general|members)/(%s$)' % reEmail,  'controllers.pgsql.alias.Profile',
    '/create/alias/(%s$)' % reDomain,                    'controllers.pgsql.alias.Create',
    '/create/alias',                                    'controllers.pgsql.alias.Create',
]
