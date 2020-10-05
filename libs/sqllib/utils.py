# Author: Zhang Huangbin <zhb@iredmail.org>

import web

from libs import iredutils
from libs.logger import log_activity
from libs.sqllib import SQLWrap
from libs.sqllib import domain as sql_lib_domain
from libs.sqllib import admin as sql_lib_admin
from libs.sqllib import user as sql_lib_user

session = web.config.get('_session', {})


def set_account_status(conn,
                       accounts,
                       account_type,
                       enable_account=False):
    """Set account status.

    accounts -- an iterable object (list/tuple) filled with accounts.
    account_type -- possible value: domain, admin, user, alias
    enable_account -- possible value: True, False
    """
    if account_type in ['admin', 'user']:
        # email
        accounts = [str(v).lower() for v in accounts if iredutils.is_email(v)]
    else:
        # domain name
        accounts = [str(v).lower() for v in accounts if iredutils.is_domain(v)]

    if not accounts:
        return (True, )

    # 0: disable, 1: enable
    account_status = 0
    action = 'disable'
    if enable_account:
        account_status = 1
        action = 'active'

    if account_type == 'domain':
        # handle with function which handles admin privilege
        qr = sql_lib_domain.enable_disable_domains(domains=accounts,
                                                   action=action)
        return qr
    elif account_type == 'admin':
        # [(<table>, <column-used-for-query>), ...]
        table_column_maps = [("admin", "username")]
    elif account_type == 'alias':
        table_column_maps = [
            ("alias", "address"),
            ("forwardings", "address"),
        ]
    else:
        # account_type == 'user'
        table_column_maps = [
            ("mailbox", "username"),
            ("forwardings", "address"),
        ]

    for (_table, _column) in table_column_maps:
        sql_where = '{} IN {}'.format(_column, web.sqlquote(accounts))
        try:
            conn.update(_table,
                        where=sql_where,
                        active=account_status)

        except Exception as e:
            return (False, repr(e))

    log_activity(event=action,
                 msg="{} {}: {}.".format(action.title(), account_type, ', '.join(accounts)))
    return (True, )


def delete_accounts(accounts,
                    account_type,
                    keep_mailbox_days=0,
                    conn=None):
    # accounts must be a list/tuple.
    # account_type in ['domain', 'user', 'admin', 'alias']
    if not accounts:
        return (True, )

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    if account_type == 'domain':
        qr = sql_lib_domain.delete_domains(domains=accounts,
                                           keep_mailbox_days=keep_mailbox_days,
                                           conn=conn)
        return qr
    elif account_type == 'user':
        sql_lib_user.delete_users(accounts=accounts,
                                  keep_mailbox_days=keep_mailbox_days,
                                  conn=conn)
    elif account_type == 'admin':
        sql_lib_admin.delete_admins(mails=accounts, conn=conn)

    return (True, )
