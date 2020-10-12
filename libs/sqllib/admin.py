# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings
from libs import iredutils, iredpwd, form_utils
from libs.logger import log_traceback, log_activity
from libs.sqllib import SQLWrap
from libs.sqllib import general as sql_lib_general

session = web.config.get('_session', {})


def is_admin_exists(conn, admin):
    # Return True if account is invalid or exist.
    admin = str(admin).lower()
    if not iredutils.is_email(admin):
        return True

    try:
        qr = conn.select(
            'admin',
            vars={'username': admin},
            what='username',
            where='username=$username',
            limit=1,
        )

        if qr:
            # Exists.
            return True

        return False
    except:
        # Return True as exist to not allow to create new domain/account.
        return True


def num_admins(conn):
    # Count separated admin accounts
    num = 0
    qr = conn.select('admin', what='COUNT(username) AS total')
    if qr:
        num = qr[0].total or 0

    return num


def num_user_admins(conn):
    # Count number of users which are marked as admins
    num = 0
    qr = conn.select(
        'mailbox',
        what='COUNT(username) AS total',
        where='isadmin=1 OR isglobaladmin=1',
    )
    if qr:
        num = qr[0].total or 0

    return num


def get_all_admins(columns=None, email_only=False, conn=None):
    """List all admins. Return (True, [records])."""
    sql_what = '*'
    if columns:
        sql_what = ','.join(columns)

    records = []
    try:
        if not conn:
            _wrap = SQLWrap()
            conn = _wrap.conn

        # standalone admin accounts
        qr = conn.select('admin',
                         what=sql_what,
                         order='username')

        for i in qr:
            records += [i]

        # mail users with admin privileges
        qr = conn.select('mailbox',
                         what=sql_what,
                         where='isadmin=1 OR isglobaladmin=1',
                         order='username')

        for i in qr:
            records += [i]

        if email_only:
            _emails = []

            for rcd in records:
                _mail = str(rcd.username).lower()
                if _mail not in _emails:
                    _emails += [_mail]

            _emails.sort()

            return (True, _emails)

        return (True, records)
    except Exception as e:
        log_traceback()
        return (False, repr(e))


def get_paged_admins(conn, cur_page=1):
    # Get current page.
    cur_page = int(cur_page)

    sql_limit = ''
    if cur_page > 0:
        sql_limit = 'LIMIT %d OFFSET %d' % (
            settings.PAGE_SIZE_LIMIT,
            (cur_page - 1) * settings.PAGE_SIZE_LIMIT,
        )

    try:
        # Get number of total accounts
        total = num_admins(conn) + num_user_admins(conn)

        # Get records
        # Separate admins
        qr_admins = conn.query(
            """
            SELECT name, username, language, active
              FROM admin
          ORDER BY username ASC
            %s
            """ % (sql_limit)
        )

        qr_user_admins = conn.query(
            """
            SELECT name, username, language, active, isadmin, isglobaladmin
              FROM mailbox
             WHERE (isadmin=1 OR isglobaladmin=1)
          ORDER BY username ASC
            %s
            """ % (sql_limit)
        )
        return (True, {'total': total, 'records': list(qr_admins) + list(qr_user_admins)})
    except Exception as e:
        log_traceback()
        return (False, repr(e))


def get_paged_domain_admins(conn,
                            domain,
                            include_global_admins=False,
                            columns=None,
                            current_page=1,
                            first_char=None):
    """Get all admins who have privilege to manage specified domain."""
    if columns:
        sql_what = ','.join(columns)
    else:
        sql_what = '*'

    if include_global_admins:
        sql_where = """username IN (
                       SELECT username FROM domain_admins
                       WHERE domain IN ('%s', 'ALL'))""" % domain
    else:
        sql_where = """username IN (
                       SELECT username FROM domain_admins
                       WHERE domain='%s')""" % domain

    if first_char:
        sql_where += ' AND username LIKE %s' % web.sqlquote(first_char.lower() + '%')

    total = 0
    all_admins = []
    try:
        qr_total = conn.select('mailbox',
                               what='COUNT(username) AS total',
                               where=sql_where)

        if qr_total:
            total = qr_total[0].total or 0
            qr = conn.select('mailbox',
                             what=sql_what,
                             where=sql_where,
                             limit=settings.PAGE_SIZE_LIMIT,
                             offset=(current_page - 1) * settings.PAGE_SIZE_LIMIT)

            for i in qr:
                all_admins += [i]

        return (True, {'total': total, 'records': all_admins})
    except Exception as e:
        log_traceback()
        return (False, repr(e))


def get_all_global_admins(conn=None):
    admins = []

    try:
        if not conn:
            _wrap = SQLWrap()
            conn = _wrap.conn

        qr = conn.select('domain_admins',
                         what='username',
                         where="domain='ALL'")

        for r in qr:
            admins += [str(r.username).lower()]

        admins.sort()
        return (True, admins)
    except Exception as e:
        log_traceback()
        return (False, repr(e))


# Get domains under control.
def get_managed_domains(admin,
                        domain_name_only=False,
                        listed_only=False,
                        conn=None):
    admin = str(admin).lower()

    if not iredutils.is_email(admin):
        return (False, 'INCORRECT_USERNAME')

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    try:
        if sql_lib_general.is_global_admin(admin=admin, conn=conn):
            if listed_only:
                result = conn.query(
                    """
                    SELECT domain.domain
                      FROM domain
                 LEFT JOIN domain_admins ON (domain.domain=domain_admins.domain)
                     WHERE domain_admins.username=$admin
                     ORDER BY domain_admins.domain
                    """,
                    vars={'admin': admin})
            else:
                result = conn.select('domain',
                                     what='domain',
                                     order='domain')
        else:
            sql_left_join = ''
            if not listed_only:
                sql_left_join = """OR domain_admins.domain='ALL'"""

            result = conn.query(
                """
                SELECT domain.domain
                  FROM domain
             LEFT JOIN domain_admins ON (domain.domain=domain_admins.domain %s)
                 WHERE domain_admins.username=$admin
              ORDER BY domain_admins.domain
                """ % (sql_left_join),
                vars={'admin': admin})

        if domain_name_only:
            domains = []
            for i in result:
                _domain = str(i['domain']).lower()
                if iredutils.is_domain(_domain):
                    domains.append(_domain)

            return (True, domains)
        else:
            return (True, list(result))
    except Exception as e:
        log_traceback()
        return (False, repr(e))


def num_managed_domains(admin=None,
                        disabled_only=False,
                        first_char=None,
                        conn=None):
    num = 0

    if not admin:
        admin = session.get('username')

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    sql_where = ''
    if disabled_only is True:
        sql_where += 'domain.active=0'

    if first_char:
        first_char = first_char[0].lower()

        if sql_where:
            sql_where += ' AND domain.domain LIKE %s' % web.sqlquote(first_char + '%')
        else:
            sql_where += 'domain.domain LIKE %s' % web.sqlquote(first_char + '%')

    try:
        if sql_lib_general.is_global_admin(admin=admin, conn=conn):
            qr = conn.select('domain', what='COUNT(domain) AS total', where=sql_where or None)
        else:
            if sql_where:
                sql_where = 'AND ' + sql_where

            qr = conn.query(
                """
                SELECT COUNT(domain.domain) AS total
                FROM domain
                LEFT JOIN domain_admins ON (domain.domain=domain_admins.domain)
                WHERE domain_admins.username=$admin %s
                """ % (sql_where),
                vars={'admin': admin})

        num = qr[0].total or 0
    except:
        log_traceback()

    return num


def num_managed_users(admin=None, domains=None, conn=None, listed_only=False):
    """Count users of all managed domains."""
    num = 0

    if not admin:
        admin = session.get('username')

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    if domains:
        domains = [str(d).lower() for d in domains if iredutils.is_domain(d)]
    else:
        qr = get_managed_domains(conn=conn,
                                 admin=admin,
                                 domain_name_only=True,
                                 listed_only=listed_only)
        if qr[0]:
            domains = qr[1]

    if not domains:
        return num

    sql_vars = {'admin': admin, 'domains': domains}

    try:
        if sql_lib_general.is_global_admin(admin=admin, conn=conn):
            if domains:
                qr = conn.select('mailbox',
                                 vars=sql_vars,
                                 what='COUNT(username) AS total',
                                 where='domain IN $domains')
            else:
                qr = conn.select('mailbox', what='COUNT(username) AS total')
        else:
            sql_append_where = ''
            if domains:
                sql_append_where = 'AND mailbox.domain IN %s' % web.sqlquote(domains)

            qr = conn.query(
                """
                SELECT COUNT(mailbox.username) AS total
                FROM mailbox
                LEFT JOIN domain_admins ON (mailbox.domain = domain_admins.domain)
                WHERE domain_admins.username=$admin %s
                """ % (sql_append_where),
                vars=sql_vars,
            )

        num = qr[0].total or 0
    except:
        log_traceback()

    return num


def __num_allocated_accounts(admin=None,
                             domains=None,
                             conn=None,
                             listed_only=False):
    """Count allocated users/aliases/lists of all managed domains."""
    num = {'users': 0, 'aliases': 0, 'lists': 0}

    if not admin:
        admin = session.get('username')

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    if domains:
        domains = [str(d).lower() for d in domains if iredutils.is_domain(d)]
    else:
        qr = get_managed_domains(conn=conn,
                                 admin=admin,
                                 domain_name_only=True,
                                 listed_only=listed_only)
        if qr[0]:
            domains = qr[1]

    if not domains:
        return num

    sql_vars = {'admin': admin, 'domains': domains}

    try:
        if sql_lib_general.is_global_admin(admin=admin, conn=conn):
            sql_what = 'SUM(mailboxes) AS mailboxes, SUM(aliases) AS aliases, SUM(maillists) AS maillists'

            if domains:
                qr = conn.select('domain',
                                 vars=sql_vars,
                                 what=sql_what,
                                 where='domain IN $domains')
            else:
                qr = conn.select('domain', what=sql_what)
        else:
            sql_what = 'SUM(domain.mailboxes) AS mailboxes, SUM(domain.aliases) AS aliases, SUM(domain.maillists) as maillists'

            sql_append_where = ''
            if domains:
                sql_append_where = 'AND domain.domain IN %s' % web.sqlquote(domains)

            qr = conn.query("""
                            SELECT %s
                            FROM domain
                            LEFT JOIN domain_admins ON (domain.domain = domain_admins.domain)
                            WHERE domain_admins.username=$admin %s
                            """ % (sql_what, sql_append_where),
                            vars=sql_vars)

        if qr:
            _qr = list(qr)[0]
            num['users'] = int(_qr.mailboxes) or 0
    except:
        log_traceback()

    return num


def sum_all_allocated_domain_quota(admin=None,
                                   domains=None,
                                   listed_only=True,
                                   conn=None):
    """Sum all allocated quota of managed domains.

    (True, <inteter>) if success.
    (False, <error_reason>) if failed to sum.
    """
    num = 0

    if not admin:
        admin = session.get('username')

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    if not domains:
        qr = get_managed_domains(conn=conn,
                                 admin=admin,
                                 domain_name_only=True,
                                 listed_only=listed_only)
        if qr[0]:
            domains = qr[1]

    if not domains:
        return (True, num)

    # Get allocated quota
    try:
        qr = conn.select('domain',
                         vars={'domains': domains},
                         what='maxquota',
                         where='domain IN $domains')

        if qr:
            for i in qr:
                if i.maxquota:
                    num += i.maxquota

        return (True, int(num))
    except Exception as e:
        log_traceback()
        return (False, repr(e))


def sum_all_used_quota(conn):
    """Sum all used quota. Return a dict: {'messages': x, 'bytes': x}."""
    d = {'messages': 0, 'bytes': 0}

    admin = session.get('username')
    if sql_lib_general.is_global_admin(admin=admin, conn=conn):
        qr = conn.query("""SELECT SUM(messages) AS messages,
                                  SUM(bytes) AS bytes
                             FROM %s""" % settings.SQL_TBL_USED_QUOTA)
        row = qr[0]
        d['messages'] = row.messages
        d['bytes'] = row.bytes

    return d


def add_admin_from_form(form, conn=None):
    mail = web.safestr(form.get('mail')).strip().lower()

    if not iredutils.is_email(mail):
        return (False, 'INVALID_MAIL')

    # Get new password.
    newpw = web.safestr(form.get('newpw'))
    confirmpw = web.safestr(form.get('confirmpw'))

    qr = iredpwd.verify_new_password(newpw=newpw, confirmpw=confirmpw)
    if qr[0] is True:
        passwd = qr[1]
    else:
        return qr

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    # Check local domain
    domain = mail.split('@', 1)[-1]
    if not iredutils.is_domain(domain):
        return (False, 'INVALID_DOMAIN')

    if sql_lib_general.is_domain_exists(domain=domain, conn=conn):
        return (False, 'CAN_NOT_BE_LOCAL_DOMAIN')

    # Check admin exist.
    if is_admin_exists(conn=conn, admin=mail):
        return (False, 'ALREADY_EXISTS')

    # Name, language
    cn = form.get('cn', '')
    lang = form_utils.get_language(form)
    _status = form_utils.get_single_value(form=form, input_name='accountStatus', default_value='active')
    if _status == 'active':
        _status = 1
    else:
        _status = 0

    try:
        conn.insert('admin',
                    username=mail,
                    name=cn,
                    password=iredpwd.generate_password_hash(passwd),
                    language=lang,
                    created=iredutils.get_gmttime(),
                    active=_status)

        conn.insert('domain_admins',
                    username=mail,
                    domain='ALL',
                    created=iredutils.get_gmttime(),
                    active='1')

        log_activity(msg="Create admin: %s." % (mail), event='create')
        return (True, )
    except Exception as e:
        log_traceback()
        return (False, repr(e))


def get_profile(mail, columns=None, conn=None):
    if not iredutils.is_email(mail):
        return (False, 'INVALID_MAIL')

    if isinstance(columns, (list, tuple, set)):
        columns = ','.join(columns)
    else:
        columns = '*'

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    try:
        qr = conn.select('admin',
                         vars={'username': mail},
                         what=columns,
                         where='username=$username',
                         limit=1)

        if qr:
            return (True, list(qr)[0])
        else:
            return (False, 'NO_SUCH_ACCOUNT')
    except Exception as e:
        log_traceback()
        return (False, repr(e))


def delete_admins(mails, revoke_admin_privilege_from_user=True, conn=None):
    mails = [str(v) for v in mails if iredutils.is_email(v)]

    if not mails:
        return (True, )

    sql_vars = {'mails': mails}

    try:
        if not conn:
            _wrap = SQLWrap()
            conn = _wrap.conn

        # Standalone mail admins
        conn.delete('admin',
                    vars=sql_vars,
                    where='username IN $mails')

        conn.delete('domain_admins',
                    vars=sql_vars,
                    where='username IN $mails')

        # Unmark globa/domain admin which is mail user
        if revoke_admin_privilege_from_user:
            conn.update('mailbox',
                        vars=sql_vars,
                        where='username IN $mails AND (isadmin=1 OR isglobaladmin=1)',
                        isadmin=0,
                        isglobaladmin=0)

        log_activity(event='delete', msg="Delete admin(s): %s." % ', '.join(mails))

        return (True, )
    except Exception as e:
        log_traceback()
        return (False, repr(e))


# Domain administration relationship (stored in sql table `domain_admins`)
# Normal domain admin will have records for each managed domain, global admin
# has only one record:
#
#   - normal admin: "username=<mail> AND domain='<domain>'"
#   - global admin: "username=<mail> AND domain='ALL'"
# NOTE: word 'ALL' is in upper cases.
def update(mail, profile_type, form, conn=None):
    mail = str(mail).lower()

    # Don't allow to view/update other admins' profile.
    if mail != session.get('username') and not session.get('is_global_admin'):
        return (False, 'PERMISSION_DENIED')

    sql_vars = {'username': mail}

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    params = {}
    if profile_type == 'general':
        # Name, preferred language
        params['name'] = form.get('cn', '')
        params['language'] = form_utils.get_language(form)

        # Update account status
        params['active'] = 0
        if 'accountStatus' in form:
            params['active'] = 1
    elif profile_type == 'password':
        newpw = web.safestr(form.get('newpw', ''))
        confirmpw = web.safestr(form.get('confirmpw', ''))

        # Verify new passwords.
        qr = iredpwd.verify_new_password(newpw=newpw, confirmpw=confirmpw)
        if qr[0] is True:
            passwd = iredpwd.generate_password_hash(qr[1])

            params['password'] = passwd
            params['passwordlastchange'] = iredutils.get_gmttime()
        else:
            return qr

    if params:
        try:
            conn.update('admin',
                        vars=sql_vars,
                        where='username=$username',
                        **params)
        except Exception as e:
            log_traceback()
            if 'password' in params:
                raise web.seeother('/profile/admin/password/{}?msg={}'.format(mail, web.urlquote(e)))
            else:
                raise web.seeother('/profile/admin/general/{}?msg={}'.format(mail, web.urlquote(e)))

    return (True, )


def revoke_admin_privilege_if_no_managed_domains(admin=None, conn=None):
    """If given admin doesn't manage any domain, revoke the admin privilege.

    @admin -- email address of domain admin
    @conn -- sql connection cursor
    """
    if not admin:
        return (True, )

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    # Return immediately if it's a global admin
    if sql_lib_general.is_global_admin(admin=admin, conn=conn):
        return (True, )

    if not num_managed_domains(admin=admin, conn=conn):
        try:
            conn.update('mailbox',
                        vars={'admin': admin},
                        isadmin=0,
                        where='username=$admin')
        except Exception as e:
            log_traceback()
            return (False, repr(e))

    return (True, )
