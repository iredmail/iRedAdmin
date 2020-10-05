# Author: Zhang Huangbin <zhb@iredmail.org>

from libs.regxes import email as e, domain as d

# fmt: off
urls = [
    # Make url ending with or without '/' going to the same class.
    '/(.*)/', 'controllers.utils.Redirect',

    '/', 'controllers.ldap.basic.Login',
    '/login', 'controllers.ldap.basic.Login',
    '/logout', 'controllers.ldap.basic.Logout',
    '/dashboard', 'controllers.ldap.basic.Dashboard',

    # Perform some operations from search page.
    '/action/(domain)', 'controllers.ldap.basic.OperationsFromSearchPage',
    '/action/(admin)', 'controllers.ldap.basic.OperationsFromSearchPage',
    '/action/(user)', 'controllers.ldap.basic.OperationsFromSearchPage',

    # Domain related.
    '/domains', 'controllers.ldap.domain.List',
    r'/domains/page/(\d+)', 'controllers.ldap.domain.List',
    # List disabled accounts.
    '/domains/disabled', 'controllers.ldap.domain.ListDisabled',
    r'/domains/disabled/page/(\d+)', 'controllers.ldap.domain.ListDisabled',
    # Profiles
    '/profile/domain/(general)/(%s$)' % d, 'controllers.ldap.domain.Profile',
    '/profile/domain/(admins)/(%s$)' % d, 'controllers.ldap.domain.Profile',
    '/profile/domain/(advanced)/(%s$)' % d, 'controllers.ldap.domain.Profile',
    '/profile/domain/(%s)' % d, 'controllers.ldap.domain.Profile',
    '/create/domain', 'controllers.ldap.domain.Create',

    # Admin related.
    '/admins', 'controllers.ldap.admin.List',
    r'/admins/page/(\d+)', 'controllers.ldap.admin.List',
    '/profile/admin/(general)/(%s$)' % e, 'controllers.ldap.admin.Profile',
    '/profile/admin/(password)/(%s$)' % e, 'controllers.ldap.admin.Profile',
    '/create/admin', 'controllers.ldap.admin.Create',

    '/create/(user)', 'controllers.ldap.utils.CreateDispatcher',

    # User related
    # List users, delete users under same domain.
    '/users/(%s$)' % d, 'controllers.ldap.user.Users',
    r'/users/(%s)/page/(\d+)' % d, 'controllers.ldap.user.Users',
    # List disabled accounts.
    '/users/(%s)/disabled' % d, 'controllers.ldap.user.DisabledUsers',
    r'/users/(%s)/disabled/page/(\d+)' % d, 'controllers.ldap.user.DisabledUsers',
    # Create user.
    '/create/user/(%s$)' % d, 'controllers.ldap.user.Create',
    # Profile pages.
    '/profile/user/(general)/(%s$)' % e, 'controllers.ldap.user.Profile',
    '/profile/user/(password)/(%s$)' % e, 'controllers.ldap.user.Profile',
    '/profile/user/(advanced)/(%s$)' % e, 'controllers.ldap.user.Profile',

    # Internal domain admins
    '/admins/(%s$)' % d, 'controllers.ldap.user.Admin',
    r'/admins/(%s)/page/(\d+)' % d, 'controllers.ldap.user.Admin',
]
