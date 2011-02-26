# Author: Zhang Huangbin <zhb@iredmail.org>

from libs.iredutils import reEmail, reDomain
 
urls = [
    # Make url ending with or without '/' going to the same class.
    '/(.*)/',                           'controllers.base.redirect',

    # used to display jpegPhoto.
    '/img/(.*)',                        'controllers.base.img',

    '/',                                'controllers.ldap.basic.Login',
    '/login',                           'controllers.ldap.basic.Login',
    '/logout',                          'controllers.ldap.basic.Logout',
    '/dashboard',                       'controllers.ldap.basic.Dashboard',
    '/dashboard/(checknew)',              'controllers.ldap.basic.Dashboard',

    # Domain related.
    '/domains',                                     'controllers.ldap.domain.List',
    '/domains/page/(\d+)',                          'controllers.ldap.domain.List',
    '/profile/domain/(general)/(%s)' % reDomain,  'controllers.ldap.domain.Profile',
    '/profile/domain/(%s)' % reDomain,             'controllers.ldap.domain.Profile',
    '/create/domain',                               'controllers.ldap.domain.Create',

    # Admin related.
    '/admins',                                      'controllers.ldap.admin.List',
    '/profile/admin/(general|password)/(%s)' % reEmail,     'controllers.ldap.admin.Profile',
    '/create/admin',                                'controllers.ldap.admin.Create',

    #########################
    # User related
    #
    # List users, delete users under same domain.
    '/users',                                       'controllers.ldap.user.List',
    '/users/(%s)' % reDomain,                       'controllers.ldap.user.List',
    '/users/(%s)/page/(\d+)' % reDomain,            'controllers.ldap.user.List',
    # Create user.
    '/create/user/(%s)' % reDomain,                'controllers.ldap.user.Create',
    '/create/user',                               'controllers.ldap.user.Create',
    # Profile pages.
    '/profile/user/(general|password)/(%s)' % reEmail,      'controllers.ldap.user.Profile',
]
