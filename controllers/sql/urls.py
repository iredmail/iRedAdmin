# Author: Zhang Huangbin <zhb@iredmail.org>

from libs.regxes import email as e, domain as d

# fmt: off
urls = [
    # Make url ending with or without '/' going to the same class.
    '/(.*)/', 'controllers.utils.Redirect',

    '/', 'controllers.sql.basic.Login',
    '/login', 'controllers.sql.basic.Login',
    '/logout', 'controllers.sql.basic.Logout',
    '/dashboard', 'controllers.sql.basic.Dashboard',

    # Domain related.
    '/domains', 'controllers.sql.domain.List',
    r'/domains/page/(\d+)', 'controllers.sql.domain.List',
    # List disabled accounts.
    '/domains/disabled', 'controllers.sql.domain.ListDisabled',
    r'/domains/disabled/page/(\d+)', 'controllers.sql.domain.ListDisabled',
    # Domain profiles
    '/profile/domain/(general)/(%s$)' % d, 'controllers.sql.domain.Profile',
    '/profile/domain/(advanced)/(%s$)' % d, 'controllers.sql.domain.Profile',
    '/profile/domain/(%s)' % d, 'controllers.sql.domain.Profile',
    '/create/domain', 'controllers.sql.domain.Create',

    # Admin related.
    '/admins', 'controllers.sql.admin.List',
    r'/admins/page/(\d+)', 'controllers.sql.admin.List',
    '/profile/admin/(general)/(%s$)' % e, 'controllers.sql.admin.Profile',
    '/profile/admin/(password)/(%s$)' % e, 'controllers.sql.admin.Profile',
    '/create/admin', 'controllers.sql.admin.Create',

    # Redirect to first mail domain.
    '/create/(user)', 'controllers.sql.utils.CreateDispatcher',

    # User related.
    '/users/(%s$)' % d, 'controllers.sql.user.List',
    r'/users/(%s)/page/(\d+)' % d, 'controllers.sql.user.List',
    # List disabled accounts.
    '/users/(%s)/disabled' % d, 'controllers.sql.user.ListDisabled',
    r'/users/(%s)/disabled/page/(\d+)' % d, 'controllers.sql.user.ListDisabled',
    # Create user.
    '/create/user/(%s$)' % d, 'controllers.sql.user.Create',
    # Profile pages.
    '/profile/user/(general)/(%s$)' % e, 'controllers.sql.user.Profile',
    '/profile/user/(password)/(%s$)' % e, 'controllers.sql.user.Profile',
    '/profile/user/(advanced)/(%s$)' % e, 'controllers.sql.user.Profile',
]
