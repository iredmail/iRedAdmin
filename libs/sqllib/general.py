# Author: Zhang Huangbin <zhb@iredmail.org>

# WARNING: this file/module will be imported by other modules under
#          libs/sqllib/, to avoid chained import loop, do not import any
#          other modules under libs/sqllib/ in this file.

from typing import Dict, Tuple
import web
from libs import iredutils
from libs.logger import logger, log_traceback
from libs.sqllib import SQLWrap, sqlutils
import settings

session = web.config.get('_session', {})


def is_global_admin(admin, conn=None) -> bool:
    if not admin:
        return False

    if admin == session.get('username'):
        if session.get('is_global_admin'):
            return True
        else:
            return False

    # Not logged admin.
    try:
        if not conn:
            _wrap = SQLWrap()
            conn = _wrap.conn

        qr = conn.select('domain_admins',
                         vars={'username': admin, 'domain': 'ALL'},
                         what='username',
                         where='username=$username AND domain=$domain',
                         limit=1)
        if qr:
            return True
        else:
            return False
    except:
        return False


def is_domain_admin(domain, admin=None, conn=None) -> bool:
    if (not iredutils.is_domain(domain)) or (not iredutils.is_email(admin)):
        return False

    if not admin:
        admin = session.get('username')

    if admin == session.get('username') and session.get('is_global_admin'):
        return True

    try:
        if not conn:
            _wrap = SQLWrap()
            conn = _wrap.conn

        qr = conn.select(
            'domain_admins',
            vars={'domain': domain, 'username': admin},
            what='username',
            where='domain=$domain AND username=$username AND active=1',
            limit=1,
        )

        if qr:
            return True
        else:
            return False
    except:
        return False


def is_email_exists(mail, conn=None) -> bool:
    # Return True if account is invalid or exist.
    if not iredutils.is_email(mail):
        return True

    mail = iredutils.strip_mail_ext_address(mail)

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    try:
        # `forwardings` table has email addr of mail user account and alias account.
        qr = conn.select('forwardings',
                         vars={'mail': mail},
                         what='address',
                         where='address=$mail',
                         limit=1)

        if qr:
            return True

        # Check `alias` for alias account which doesn't have any member.
        qr = conn.select('alias',
                         vars={'mail': mail},
                         what='address',
                         where='address=$mail',
                         limit=1)
        if qr:
            return True

        return False
    except Exception:
        return True


def __is_account_exists(account, account_type, conn=None) -> bool:
    """Check whether mail alias account exists."""
    if account_type == 'domain':
        if not iredutils.is_domain(account):
            return True

        account = account.lower()
    else:
        if not iredutils.is_email(account):
            return False

        account = iredutils.strip_mail_ext_address(account)

    # {<account_type: [(<sql-table>, <sql-column-name>), ...]}
    _maps = {
        "domain": [
            ("domain", "domain"),
            ("alias_domain", "alias_domain"),
        ],
        "user": [("mailbox", "username")],
        "alias": [("alias", "address")],
        "ml": [("maillists", "address")],
    }

    if account_type not in _maps:
        return False

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    try:
        for (_table, _column) in _maps[account_type]:
            qr = conn.select(_table,
                             vars={'account': account},
                             what=_column,
                             where='%s=$account' % _column,
                             limit=1)

            if qr:
                return True
    except:
        log_traceback()
        return False

    return False


def is_domain_exists(domain, conn=None) -> bool:
    return __is_account_exists(account=domain, account_type='domain', conn=conn)


def is_ml_exists(mail, conn=None) -> bool:
    return __is_account_exists(account=mail, account_type='ml', conn=conn)


def __is_active_account(account_type, account, conn=None) -> bool:
    """Check whether given account is active."""
    account = str(account).lower()

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    # {<account_type>: (<table>, <column>)}
    _maps = {
        "user": ("mailbox", "username"),
        "alias": ("alias", "address"),
        "ml": ("maillists", "address"),
        "domain": ("domain", "domain"),
        "admin": ("admin", "username"),
    }

    if account_type not in _maps:
        return False

    (_table, _column) = _maps[account_type]

    try:
        qr = conn.select(_table,
                         vars={'account': account},
                         what="active",
                         where="%s=$account AND active=1" % _column,
                         limit=1)

        if qr:
            return True
    except Exception as e:
        logger.error("Error while checking whether account is active: {}.".format(e))

    return False


def is_active_user(mail, conn=None) -> bool:
    return __is_active_account(account_type='user', account=mail, conn=conn)


def filter_existing_emails(mails, account_type=None, conn=None):
    """
    Remove non-existing addresses in given list, return a list of existing ones.

    :param mails: list of email addresses
    :param account_type: user, alias, maillist.
    :param conn: sql connection cursor
    """
    exist = []
    nonexist = []

    mails = [i for i in mails if iredutils.is_email(i)]

    if not mails:
        return {'exist': exist, 'nonexist': nonexist}

    # A dict with email addresses without and with mail extension.
    d = {}
    for i in mails:
        _addr_without_ext = iredutils.strip_mail_ext_address(i)
        d[_addr_without_ext] = i

    emails_without_ext = list(d.keys())

    # {<account_type>: {'table': <sql_table_name>, 'column': <sql_column_name>}}
    _tbl_column_maps = {
        'user': [("forwardings", "address"), ("mailbox", "username")],
        'alias': [("alias", "address")],
        'maillist': [("maillists", "address")],
    }

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    try:
        _tbl_and_columns = []
        if account_type:
            _tbl_and_columns += _tbl_column_maps[account_type]
        else:
            for v in list(_tbl_column_maps.values()):
                _tbl_and_columns += v

        for (_table, _column) in _tbl_and_columns:
            # Removing verified addresses to query less values for better SQL
            # query performance.
            _pending_emails = [i for i in emails_without_ext if i not in exist]
            if not _pending_emails:
                break

            qr = conn.select(_table,
                             vars={'mails': _pending_emails},
                             what='%s' % _column,
                             where='%s IN $mails' % _column,
                             group='%s' % _column)

            if qr:
                for row in qr:
                    _addr = str(row[_column]).lower()
                    exist.append(d[_addr])

        exist = list(set(exist))
        nonexist = [d[k] for k in d if k not in exist]
    except:
        log_traceback()

    return {'exist': exist, 'nonexist': nonexist}


def filter_existing_domains(conn, domains):
    domains = [str(v).lower() for v in domains if iredutils.is_domain(v)]
    domains = list(set(domains))

    exist = []
    nonexist = []

    try:
        # Primary domains
        qr1 = conn.select('domain',
                          vars={'domains': domains},
                          what='domain',
                          where='domain IN $domains')

        # Alias domains
        qr2 = conn.select('alias_domain',
                          vars={'domains': domains},
                          what='alias_domain AS domain',
                          where='alias_domain IN $domains')

        qr = list(qr1) + list(qr2)
        if not qr:
            nonexist = domains
        else:
            for i in qr:
                exist.append(str(i['domain']).lower())

            nonexist = [d for d in domains if d not in exist]
    except:
        pass

    return {'exist': exist, 'nonexist': nonexist}


# Do not apply @decorators.require_global_admin
def get_domain_settings(domain, domain_profile=None, conn=None):
    domain = str(domain).lower()

    try:
        if not domain_profile:
            if not conn:
                _wrap = SQLWrap()
                conn = _wrap.conn

            qr = conn.select('domain',
                             vars={'domain': domain},
                             what='settings',
                             where='domain=$domain',
                             limit=1)

            if qr:
                domain_profile = list(qr)[0]
            else:
                return (False, 'INVALID_DOMAIN_NAME')

        ps = domain_profile.get('settings', '')
        ds = sqlutils.account_settings_string_to_dict(ps)

        return (True, ds)
    except Exception as e:
        return (False, repr(e))


def get_user_settings(mail, existing_settings=None, conn=None):
    """Return dict of per-user settings stored in SQL column: mailbox.settings.

    :param mail: full user email address.
    :param existing_settings: original value of sql column `mailbox.settings`.
    :param conn: sql connection cursor.
    """
    if not iredutils.is_email(mail):
        return (False, 'INVALID_MAIL')

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    user_settings = {}

    # Get settings stored in sql column `mailbox.settings`
    if existing_settings:
        orig_settings = existing_settings
    else:
        try:
            qr = conn.select('mailbox',
                             vars={'username': mail},
                             what='settings',
                             where='username=$username',
                             limit=1)

            if qr:
                orig_settings = qr[0]['settings']
            else:
                return (False, 'NO_SUCH_ACCOUNT')
        except Exception as e:
            return (False, repr(e))

    if orig_settings:
        user_settings = sqlutils.account_settings_string_to_dict(orig_settings)

    return (True, user_settings)


def get_admin_settings(admin=None, existing_settings=None, conn=None) -> Tuple:
    """Return a dict of per-admin settings.

    :param admin: mail address of domain admin
    :param existing_settings: original value of sql column `settings`
    :param conn: SQL connection cursor
    """
    if not admin:
        admin = session.get('username')

    if not iredutils.is_email(admin):
        return (False, 'INVALID_ADMIN')

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    account_settings = {}

    # Get settings stored in sql column `mailbox.settings`
    if existing_settings:
        orig_settings = existing_settings
    else:
        try:
            qr = conn.select('mailbox',
                             vars={'username': admin},
                             what='settings',
                             where='username=$username AND (isadmin=1 OR isglobaladmin=1)',
                             limit=1)

            if not qr:
                # Not a mail user
                qr = conn.select('admin',
                                 vars={'username': admin},
                                 what='settings',
                                 where='username=$username',
                                 limit=1)
                if not qr:
                    return (False, 'INVALID_ADMIN')

            orig_settings = qr[0]['settings']
        except Exception as e:
            return (False, repr(e))

    if orig_settings:
        account_settings = sqlutils.account_settings_string_to_dict(orig_settings)

    return (True, account_settings)


# Update SQL column `[domain|admin|mailbox].settings` in `vmail` database.
def __update_account_settings(conn,
                              account,
                              account_type='user',
                              exist_settings=None,
                              new_settings=None,
                              removed_settings=None):
    """Update account settings stored in SQL column `settings`.

    :param conn: SQL connection cursor
    :param account: the account you want to update. could be a domain, admin, user
    :param account_type: one of: domain, admin, user
    :param exist_settings: dict of account settings you already get from SQL
    :param new_settings: dict of the new settings you want to add
    :param removed_settings: list of the setting names you want to remove
    """
    account = str(account).lower()

    # Get current settings stored in SQL db
    if exist_settings:
        current_settings = exist_settings
    else:
        if account_type == 'user':
            qr = get_user_settings(mail=account, conn=conn)
        elif account_type == 'admin':
            qr = get_admin_settings(admin=account, conn=conn)
        elif account_type == 'domain':
            qr = get_domain_settings(domain=account, conn=conn)
        else:
            return (False, 'UNKNOWN_ACCOUNT_TYPE')

        if qr[0]:
            current_settings = qr[1]
        else:
            current_settings = {}

    if new_settings:
        for (k, v) in list(new_settings.items()):
            current_settings[k] = v

    if removed_settings:
        for k in removed_settings:
            try:
                current_settings.pop(k)
            except:
                pass

    # Convert settings dict to string
    settings_string = sqlutils.account_settings_dict_to_string(current_settings)

    try:
        if account_type == 'user':
            conn.update('mailbox',
                        vars={'username': account},
                        where='username=$username',
                        settings=settings_string)
        elif account_type == 'admin':
            conn.update('admin',
                        vars={'username': account},
                        where='username=$username',
                        settings=settings_string)
        elif account_type == 'domain':
            conn.update('domain',
                        vars={'domain': account},
                        where='domain=$domain',
                        settings=settings_string)

        return (True, )
    except Exception as e:
        return (False, repr(e))


def update_user_settings(conn,
                         mail,
                         exist_settings=None,
                         new_settings=None,
                         removed_settings=None):
    return __update_account_settings(conn=conn,
                                     account=mail,
                                     account_type='user',
                                     exist_settings=exist_settings,
                                     new_settings=new_settings,
                                     removed_settings=removed_settings)


def update_admin_settings(conn,
                          mail,
                          exist_settings=None,
                          new_settings=None,
                          removed_settings=None):
    return __update_account_settings(conn=conn,
                                     account=mail,
                                     account_type='admin',
                                     exist_settings=exist_settings,
                                     new_settings=new_settings,
                                     removed_settings=removed_settings)


def update_domain_settings(conn,
                           domain,
                           exist_settings=None,
                           new_settings=None,
                           removed_settings=None):
    return __update_account_settings(conn=conn,
                                     account=domain,
                                     account_type='domain',
                                     exist_settings=exist_settings,
                                     new_settings=new_settings,
                                     removed_settings=removed_settings)


def __num_accounts_under_domain(domain, account_type, conn=None) -> int:
    num = 0

    if not iredutils.is_domain(domain):
        return num

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    # mapping of account types and sql table names
    mapping = {'user': 'mailbox',
               'alias': 'alias',
               'maillist': 'maillists'}
    sql_table = mapping[account_type]

    try:
        qr = conn.select(sql_table,
                         vars={'domain': domain},
                         what='COUNT(domain) AS total',
                         where='domain=$domain')

        if qr:
            num = qr[0].total
    except Exception as e:
        logger.error(e)

    return num


def num_users_under_domain(domain, conn=None) -> int:
    return __num_accounts_under_domain(domain=domain,
                                       account_type='user',
                                       conn=conn)


def get_account_used_quota(accounts, conn) -> Dict:
    """Return dict of account/quota size pairs.

    accounts -- must be list/tuple of email addresses.
    """
    if not accounts:
        return {}

    # Pre-defined dict of used quotas.
    #   {'user@domain.com': {'bytes': INTEGER, 'messages': INTEGER,}}
    used_quota = {}

    # Get used quota.
    try:
        qr = conn.select(settings.SQL_TBL_USED_QUOTA,
                         vars={'accounts': accounts},
                         where='username IN $accounts',
                         what='username, bytes, messages')

        for uq in qr:
            used_quota[uq.username] = {'bytes': uq.get('bytes', 0),
                                       'messages': uq.get('messages', 0)}
    except:
        pass

    return used_quota


def get_first_char_of_all_accounts(domain,
                                   account_type,
                                   conn=None):
    """Get first character of accounts under given domain.

    @domain - must be a valid domain name.
    @account_type - could be one of: user, ml, alias.
    @conn - SQL connection cursor
    """
    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    type_map = {'user': {'table': 'mailbox', 'column': 'username'},
                'alias': {'table': 'alias', 'column': 'address'},
                'ml': {'table': 'maillists', 'column': 'address'}}

    _table = type_map[account_type]['table']
    _column = type_map[account_type]['column']

    chars = []
    try:
        qr = conn.select(_table,
                         vars={'domain': domain, 'column': _column},
                         what="SUBSTRING({} FROM 1 FOR 1) AS first_char".format(_column),
                         where='domain=$domain',
                         group='first_char')

        if qr:
            chars = [str(i.first_char).upper() for i in qr]
            chars.sort()

        return (True, chars)
    except Exception as e:
        log_traceback()
        return (False, repr(e))
