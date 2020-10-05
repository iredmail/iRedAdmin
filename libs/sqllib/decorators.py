# Author: Zhang Huangbin <zhb@iredmail.org>

from controllers import decorators as base_decorators

require_login = base_decorators.require_login
require_global_admin = base_decorators.require_global_admin
csrf_protected = base_decorators.csrf_protected
