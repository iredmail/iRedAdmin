# Author: Zhang Huangbin <zhb@iredmail.org>

import os
import web
import settings

from libs import iredutils, iredpwd, form_utils

from libs.l10n import TIMEZONES
from libs.logger import logger, log_activity

from libs.sqllib import SQLWrap, decorators, sqlutils
from libs.sqllib import general as sql_lib_general
from libs.sqllib import admin as sql_lib_admin
from libs.sqllib import domain as sql_lib_domain

session = web.config.get('_session', {})


def user_is_global_admin(conn, mail, user_profile=None):
    try:
        if user_profile:
            if user_profile.get('isglobaladmin', 0) == 1:
                return True
        else:
            if not conn:
                _wrap = SQLWrap()
                conn = _wrap.conn

            qr = conn.select('mailbox',
                             vars={'username': mail},
                             what='isglobaladmin',
                             where='username=$username AND isglobaladmin=1',
                             limit=1)
            if qr:
                return True
    except:
        pass

    return False


def delete_users(accounts,
                 keep_mailbox_days=0,
                 conn=None):
    accounts = [str(v) for v in accounts if iredutils.is_email(v)]

    if not accounts:
        return (True, )

    # Keep mailboxes 'forever', set to 100 years.
    try:
        keep_mailbox_days = abs(int(keep_mailbox_days))
    except:
        if session.get('is_global_admin'):
            keep_mailbox_days = 0
        else:
            _max_days = max(settings.DAYS_TO_KEEP_REMOVED_MAILBOX)
            if keep_mailbox_days > _max_days:
                # Get the max days
                keep_mailbox_days = _max_days

    if keep_mailbox_days == 0:
        sql_keep_days = web.sqlliteral('Null')
    else:
        if settings.backend == 'mysql':
            sql_keep_days = web.sqlliteral('DATE_ADD(CURDATE(), INTERVAL %d DAY)' % keep_mailbox_days)
        elif settings.backend == 'pgsql':
            sql_keep_days = web.sqlliteral("""CURRENT_TIMESTAMP + INTERVAL '%d DAYS'""" % keep_mailbox_days)

    sql_vars = {'accounts': accounts,
                'admin': session.get('username'),
                'sql_keep_days': sql_keep_days}

    # Log maildir path of deleted users.
    if settings.backend == 'mysql':
        sql_raw = '''
            INSERT INTO deleted_mailboxes (username, maildir, domain, admin, delete_date)
            SELECT username, \
                   CONCAT(storagebasedirectory, '/', storagenode, '/', maildir) AS maildir, \
                   SUBSTRING_INDEX(username, '@', -1), \
                   $admin, \
                   $sql_keep_days
              FROM mailbox
             WHERE username IN $accounts'''
    elif settings.backend == 'pgsql':
        sql_raw = '''
            INSERT INTO deleted_mailboxes (username, maildir, domain, admin, delete_date)
            SELECT username, \
                   storagebasedirectory || '/' || storagenode || '/' || maildir, \
                   SPLIT_PART(username, '@', 2), \
                   $admin, \
                   $sql_keep_days
              FROM mailbox
             WHERE username IN $accounts'''

    try:
        if not conn:
            _wrap = SQLWrap()
            conn = _wrap.conn

        conn.query(sql_raw, vars=sql_vars)
    except:
        pass

    try:
        for tbl in ['mailbox',
                    'domain_admins',
                    'recipient_bcc_user',
                    'sender_bcc_user',
                    settings.SQL_TBL_USED_QUOTA]:
            conn.delete(tbl,
                        vars=sql_vars,
                        where='username IN $accounts')

        # remove destination bcc addresses.
        for tbl in ['recipient_bcc_user',
                    'sender_bcc_user',
                    'recipient_bcc_domain',
                    'sender_bcc_domain']:
            conn.delete(tbl,
                        vars=sql_vars,
                        where='bcc_address IN $accounts')

        # Remove user from `forwardings`, including:
        #   - per-user mail forwardings
        #   - per-domain catch-all account
        #   - alias membership
        #   - alias moderators
        conn.delete('forwardings',
                    vars=sql_vars,
                    where='address IN $accounts OR forwarding IN $accounts')

        # remove destination moderators.
        conn.delete('moderators',
                    vars=sql_vars,
                    where='moderator IN $accounts')
    except Exception as e:
        return (False, repr(e))

    log_activity(event='delete',
                 domain=accounts[0].split('@', 1)[-1],
                 msg="Delete user: %s." % ', '.join(accounts))

    return (True, )


@decorators.require_global_admin
def simple_profile(mail, columns=None, conn=None):
    """Return value of sql column `mailbox.settings`.

    @columns -- a list or tuple which contains SQL column names
    """
    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    sql_what = '*'
    if columns:
        sql_what = ','.join(columns)

    try:
        qr = conn.select('mailbox',
                         vars={'username': mail},
                         what=sql_what,
                         where='username=$username',
                         limit=1)

        if qr:
            return (True, list(qr)[0])
        else:
            return (False, 'NO_SUCH_ACCOUNT')
    except Exception as e:
        return (False, repr(e))


def promote_users_to_be_global_admin(mails, promote=True, conn=None):
    mails = [str(i).lower() for i in mails if iredutils.is_email(i)]
    if not mails:
        return (True, )

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    try:
        sql_vars = {'mails': mails, 'domain': 'ALL'}
        conn.delete('domain_admins',
                    vars=sql_vars,
                    where="username IN $mails AND domain=$domain")

        if promote:
            v = []
            for i in mails:
                v += [{'username': i, 'domain': 'ALL'}]

            conn.multiple_insert('domain_admins', v)

            # Update `vmail.mailbox`
            conn.update('mailbox',
                        vars=sql_vars,
                        isglobaladmin=1,
                        where="username IN $mails")
        else:
            # Update `vmail.mailbox`
            conn.update('mailbox',
                        vars=sql_vars,
                        isglobaladmin=0,
                        where="username IN $mails")

        return (True, )
    except Exception as e:
        logger.error(e)
        return (False, repr(e))


def num_users_under_domains(conn, domains, disabled_only=False, first_char=None):
    # Count separated admin accounts
    num = 0
    if not domains:
        return num

    sql_where = ''
    if disabled_only:
        sql_where = ' AND active=0'

    if first_char:
        sql_where += ' AND username LIKE %s' % web.sqlquote(first_char.lower() + '%')

    sql_vars = {'domains': domains}
    try:
        qr = conn.select('mailbox',
                         vars=sql_vars,
                         what='COUNT(username) AS total',
                         where='domain IN $domains %s' % sql_where)
        if qr:
            num = qr[0].total or 0
    except:
        pass

    return num


@decorators.require_global_admin
def get_paged_users(conn,
                    domain,
                    cur_page=1,
                    admin_only=False,
                    order_name=None,
                    order_by_desc=None,
                    first_char=None,
                    disabled_only=False):
    domain = str(domain).lower()
    cur_page = int(cur_page) or 1

    sql_vars = {'domain': domain}
    sql_where = 'mailbox.domain=%s' % web.sqlquote(domain)

    if admin_only:
        sql_where += ' AND (mailbox.isadmin=1 OR mailbox.isglobaladmin=1)'

    if first_char:
        sql_where += ' AND mailbox.username LIKE %s' % web.sqlquote(first_char.lower() + '%')

    if disabled_only:
        sql_where += ' AND mailbox.active=0'

    try:
        if order_name == 'quota':
            if settings.backend == 'mysql':
                sql_cmd_percentage = '100 * IFNULL(%s.bytes, 0)/(mailbox.quota * 1024 * 1024) AS percentage' % settings.SQL_TBL_USED_QUOTA
            else:
                # ATTENTION:
                #   - 'COALESCE(X, 0) as percentage': set percentage of unlimited mailbox to 0
                #   - 'NULLIF()': set `mailbox.quota` of unlimited mailbox to null,
                #                 this way we can avoid PostgreSQL error: `division by zero`
                sql_cmd_percentage = 'COALESCE((100 * COALESCE(%s.bytes, 0)/(NULLIF(mailbox.quota, 0) * 1024 * 1024)), 0) as percentage' % settings.SQL_TBL_USED_QUOTA

            if order_by_desc:
                _order_by = 'DESC'
            else:
                _order_by = 'ASC'

            qr = conn.query("""
                SELECT
                    mailbox.username, mailbox.name, mailbox.quota,
                    mailbox.employeeid, mailbox.active, mailbox.isadmin,
                    mailbox.isglobaladmin, mailbox.passwordlastchange,
                    %s
                FROM mailbox
                LEFT JOIN %s ON (%s.username = mailbox.username)
                WHERE %s
                ORDER BY percentage %s, mailbox.username ASC
                LIMIT %d
                OFFSET %d
            """ % (sql_cmd_percentage,
                   settings.SQL_TBL_USED_QUOTA, settings.SQL_TBL_USED_QUOTA,
                   sql_where,
                   _order_by,
                   settings.PAGE_SIZE_LIMIT,
                   (cur_page - 1) * settings.PAGE_SIZE_LIMIT))

        elif order_name == 'name':
            sql_order = 'name ASC, username ASC'
            if order_by_desc:
                sql_order = 'name DESC, username ASC'

            qr = conn.select(
                'mailbox',
                vars=sql_vars,
                # Just query what we need to reduce memory use.
                what='username,name,quota,employeeid,active,isadmin,isglobaladmin,passwordlastchange',
                where=sql_where,
                order=sql_order,
                limit=settings.PAGE_SIZE_LIMIT,
                offset=(cur_page - 1) * settings.PAGE_SIZE_LIMIT,
            )
        else:
            qr = conn.select(
                'mailbox',
                vars=sql_vars,
                # Just query what we need to reduce memory use.
                what='username,name,quota,employeeid,active,isadmin,isglobaladmin,passwordlastchange',
                where=sql_where,
                order='username ASC',
                limit=settings.PAGE_SIZE_LIMIT,
                offset=(cur_page - 1) * settings.PAGE_SIZE_LIMIT)

        return (True, list(qr))
    except Exception as e:
        return (False, repr(e))


def mark_user_as_admin(conn,
                       domain,
                       users,
                       as_normal_admin=None,
                       as_global_admin=None):
    """Mark normal mail user accounts as domain admin.

    @domain -- specified users will be admin of this domain.
    @users -- iterable object which contains list of email addresses.
    @as_normal_admin -- True to enable, False to disable. None for no change.
    @as_global_admin -- True to enable, False to disable. None for no change.
    """
    sql_vars = {'users': users}
    sql_updates = {}

    if as_normal_admin is True:
        sql_updates['isadmin'] = 1
    elif as_normal_admin is False:
        sql_updates['isadmin'] = 0

    if session.get('is_global_admin'):
        if as_global_admin is True:
            sql_updates['isglobaladmin'] = 1
        elif as_global_admin is False:
            sql_updates['isglobaladmin'] = 0

    if not sql_updates:
        return (True, )

    try:
        # update `mailbox.isadmin`, `mailbox.isglobaladmin`.
        conn.update('mailbox',
                    vars=sql_vars,
                    where='username IN $users',
                    **sql_updates)

        if as_normal_admin is True:
            # Add records in `domain_admins` to identify admin privilege.
            for u in users:
                try:
                    conn.insert('domain_admins',
                                username=u,
                                domain=domain)
                except:
                    pass
        elif as_normal_admin is False:
            # Remove admin privilege.
            try:
                conn.delete('domain_admins',
                            vars={'users': users},
                            where="username IN $users AND domain <> 'ALL'")
            except:
                pass

        if as_global_admin is True:
            promote_users_to_be_global_admin(mails=users, promote=True, conn=conn)
        elif as_global_admin is False:
            promote_users_to_be_global_admin(mails=users, promote=False, conn=conn)

        return (True, )
    except Exception as e:
        return (False, repr(e))


def profile(mail,
            with_used_quota=True,
            conn=None):
    """Get full user profile.

    @with_alias -- get per-user alias addresses.
    @with_forwardings -- get mail forwarding addresses
    """
    mail = str(mail).lower()

    try:
        if not conn:
            _wrap = SQLWrap()
            conn = _wrap.conn

        qr = conn.select("mailbox",
                         vars={'mail': mail},
                         where="username=$mail", limit=1)

        if qr:
            p = qr[0]
            p['stored_bytes'] = 0
            p['stored_messages'] = 0

            if with_used_quota:
                _used_quota = sql_lib_general.get_account_used_quota(accounts=[mail], conn=conn)
                if mail in _used_quota:
                    p['stored_bytes'] = _used_quota[mail]['bytes']
                    p['stored_messages'] = _used_quota[mail]['messages']

            return (True, p)
        else:
            return (False, 'NO_SUCH_ACCOUNT')
    except Exception as e:
        return (False, repr(e))


def add_user_from_form(domain, form, conn=None):
    # Get domain name, username, cn.
    mail_domain = form_utils.get_domain_name(form)
    mail_username = form.get('username')
    if mail_username:
        mail_username = web.safestr(mail_username).strip().lower()
    else:
        return (False, 'INVALID_ACCOUNT')

    mail = mail_username + '@' + mail_domain

    if mail_domain != domain:
        return (False, 'PERMISSION_DENIED')

    if not iredutils.is_auth_email(mail):
        return (False, 'INVALID_MAIL')

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    # Check account existing.
    if sql_lib_general.is_email_exists(mail=mail, conn=conn):
        return (False, 'ALREADY_EXISTS')

    # Get domain profile.
    qr_profile = sql_lib_domain.profile(conn=conn, domain=domain)

    if qr_profile[0] is True:
        domain_profile = qr_profile[1]
        domain_settings = sqlutils.account_settings_string_to_dict(domain_profile['settings'])
    else:
        return qr_profile

    # Check account limit.
    num_exist_accounts = sql_lib_admin.num_managed_users(conn=conn, domains=[domain])

    if domain_profile.mailboxes == -1:
        return (False, 'NOT_ALLOWED')
    elif domain_profile.mailboxes > 0:
        if domain_profile.mailboxes <= num_exist_accounts:
            return (False, 'EXCEEDED_DOMAIN_ACCOUNT_LIMIT')

    # Get quota from <form>
    quota = str(form.get('mailQuota', 0)).strip()
    try:
        quota = int(quota)
    except:
        quota = 0

    #
    # Get password from <form>.
    #
    pw_hash = form.get('password_hash', '')
    newpw = web.safestr(form.get('newpw', ''))
    confirmpw = web.safestr(form.get('confirmpw', ''))

    if pw_hash:
        if not iredpwd.is_supported_password_scheme(pw_hash):
            return (False, 'INVALID_PASSWORD_SCHEME')

        passwd = pw_hash
    else:
        # Get password length limit from domain profile or global setting.
        min_passwd_length = domain_settings.get('min_passwd_length', 0)
        max_passwd_length = domain_settings.get('max_passwd_length', 0)

        qr_pw = iredpwd.verify_new_password(newpw,
                                            confirmpw,
                                            min_passwd_length=min_passwd_length,
                                            max_passwd_length=max_passwd_length)

        if qr_pw[0] is True:
            pwscheme = None
            if 'store_password_in_plain_text' in form and settings.STORE_PASSWORD_IN_PLAIN_TEXT:
                pwscheme = 'PLAIN'
            passwd = iredpwd.generate_password_hash(qr_pw[1], pwscheme=pwscheme)
        else:
            return qr_pw

    # Get display name from <form>
    cn = form_utils.get_single_value(form, input_name='cn', default_value='')

    # Get preferred language.
    preferred_language = form_utils.get_language(form)
    if preferred_language not in iredutils.get_language_maps():
        preferred_language = ''

    # Get storage base directory.
    _storage_base_directory = settings.storage_base_directory
    splited_sbd = _storage_base_directory.rstrip('/').split('/')
    storage_node = splited_sbd.pop()
    storage_base_directory = '/'.join(splited_sbd)
    maildir = iredutils.generate_maildir_path(mail)

    # Read full maildir path from web form - from RESTful API.
    mailbox_maildir = form.get('maildir', '').lower().rstrip('/')
    if mailbox_maildir and os.path.isabs(mailbox_maildir):
        # Split storageBaseDirectory and storageNode
        _splited = mailbox_maildir.rstrip('/').split('/')
        storage_base_directory = '/' + _splited[0]
        storage_node = _splited[1]
        maildir = '/'.join(_splited[2:])

    record = {'domain': domain,
              'username': mail,
              'password': passwd,
              'name': cn,
              'quota': quota,
              'storagebasedirectory': storage_base_directory,
              'storagenode': storage_node,
              'maildir': maildir,
              'language': preferred_language,
              'passwordlastchange': iredutils.get_gmttime(),
              'created': iredutils.get_gmttime(),
              'active': 1}

    # Get settings from SQL db.
    db_settings = iredutils.get_settings_from_db()

    # Get mailbox format and folder.
    _mailbox_format = form.get('mailboxFormat', db_settings['mailbox_format']).lower()
    _mailbox_folder = form.get('mailboxFolder', db_settings['mailbox_folder'])
    if iredutils.is_valid_mailbox_format(_mailbox_format):
        record['mailboxformat'] = _mailbox_format

    if iredutils.is_valid_mailbox_folder(_mailbox_folder):
        record['mailboxfolder'] = _mailbox_folder

    # Always store plain password in another attribute.
    if settings.STORE_PLAIN_PASSWORD_IN_ADDITIONAL_ATTR:
        record[settings.STORE_PLAIN_PASSWORD_IN_ADDITIONAL_ATTR] = newpw

    # Set disabled mail services.
    disabled_mail_services = domain_settings.get('disabled_mail_services', [])
    for srv in disabled_mail_services:
        record['enable' + srv] = 0

    # globally disabled mail services
    for srv in settings.ADDITIONAL_DISABLED_USER_SERVICES:
        record['enable' + srv] = 0

    # globally enabled mail services
    for srv in settings.ADDITIONAL_ENABLED_USER_SERVICES:
        record['enable' + srv] = 1

    try:
        # Store new user in SQL db.
        conn.insert('mailbox', **record)

        # Create an entry in `vmail.forwardings` with `address=forwarding`
        conn.insert('forwardings',
                    address=mail,
                    forwarding=mail,
                    domain=domain,
                    dest_domain=domain,
                    is_forwarding=1,
                    active=1)

        log_activity(msg="Create user: %s." % (mail),
                     domain=domain,
                     event='create')
        return (True, )
    except Exception as e:
        return (False, repr(e))


def update(conn, mail, profile_type, form):
    profile_type = web.safestr(profile_type)
    mail = str(mail).lower()
    domain = mail.split('@', 1)[-1]

    qr = sql_lib_domain.simple_profile(conn=conn,
                                       domain=domain,
                                       columns=['maxquota', 'settings'])
    if not qr[0]:
        return qr

    domain_profile = qr[1]
    del qr

    domain_settings = sqlutils.account_settings_string_to_dict(domain_profile.get('settings', ''))

    disabled_user_profiles = domain_settings.get('disabled_user_profiles', [])
    if not session.get('is_global_admin'):
        if profile_type in disabled_user_profiles:
            return (False, 'PERMISSION_DENIED')

    # Pre-defined update key:value pairs
    updates = {'modified': iredutils.get_gmttime()}

    if profile_type == 'general':
        # Get name
        updates['name'] = form.get('cn', '')

        # Get preferred language: short lang code. e.g. en_US, de_DE.
        preferred_language = form_utils.get_language(form)
        if preferred_language in iredutils.get_language_maps():
            updates['language'] = preferred_language
        else:
            updates['language'] = ''

        tz_name = form_utils.get_timezone(form)
        if tz_name:
            sql_lib_general.update_user_settings(conn=conn,
                                                 mail=mail,
                                                 new_settings={'timezone': tz_name})

            if session['username'] == mail:
                session['timezone'] = TIMEZONES[tz_name]
        else:
            sql_lib_general.update_user_settings(conn=conn,
                                                 mail=mail,
                                                 removed_settings=['timezone'])

        # Update language immediately.
        if session.get('username') == mail and \
           session.get('lang', 'en_US') != preferred_language:
            session['lang'] = preferred_language

        # check account status
        updates['active'] = 0
        if 'accountStatus' in form:
            updates['active'] = 1

        # Update account status in table `alias` immediately
        try:
            conn.update('forwardings',
                        vars={'address': mail},
                        where='address=$address OR forwarding=$address',
                        active=updates['active'])
        except:
            pass

        # Get mail quota size.
        mailQuota = str(form.get('mailQuota'))
        if mailQuota.isdigit():
            mailQuota = int(mailQuota)
        else:
            mailQuota = 0

        updates['quota'] = mailQuota
        updates['employeeid'] = form.get('employeeNumber', '')

    elif profile_type == 'password':
        newpw = web.safestr(form.get('newpw', ''))
        confirmpw = web.safestr(form.get('confirmpw', ''))

        # Get password length limit from domain profile or global setting.
        min_passwd_length = domain_settings.get('min_passwd_length', 0)
        max_passwd_length = domain_settings.get('max_passwd_length', 0)

        # Verify new passwords.
        qr = iredpwd.verify_new_password(newpw=newpw,
                                         confirmpw=confirmpw,
                                         min_passwd_length=min_passwd_length,
                                         max_passwd_length=max_passwd_length)
        if qr[0] is True:
            pwscheme = None
            if 'store_password_in_plain_text' in form and settings.STORE_PASSWORD_IN_PLAIN_TEXT:
                pwscheme = 'PLAIN'
            passwd = iredpwd.generate_password_hash(qr[1], pwscheme=pwscheme)
        else:
            return qr

        # Hash/encrypt new password.
        updates['password'] = passwd
        updates['passwordlastchange'] = iredutils.get_gmttime()

        # Store plain password in another attribute.
        if settings.STORE_PLAIN_PASSWORD_IN_ADDITIONAL_ATTR:
            updates[settings.STORE_PLAIN_PASSWORD_IN_ADDITIONAL_ATTR] = newpw
    else:
        return (True, )

    # Update SQL db
    try:
        conn.update('mailbox',
                    vars={'username': mail},
                    where='username=$username',
                    **updates)

        log_activity(msg="Update user profile ({}): {}.".format(profile_type, mail),
                     admin=session.get('username'),
                     username=mail,
                     domain=domain,
                     event='update')

        return (True, {})
    except Exception as e:
        return (False, repr(e))


def get_basic_user_profiles(domain,
                            columns=None,
                            first_char=None,
                            page=0,
                            disabled_only=False,
                            email_only=False,
                            conn=None):
    """Get basic user profiles under given domain.

    Return data:
        (True, [{'mail': 'list@domain.com',
                 'name': '...',
                 ...other profiles in `vmail.maillists` table...
                 }])
    """
    domain = web.safestr(domain).lower()
    if not iredutils.is_domain(domain):
        raise web.seeother('/domains?msg=INVALID_DOMAIN_NAME')

    sql_vars = {'domain': domain}

    if columns:
        sql_what = ','.join(columns)
    else:
        if email_only:
            sql_what = 'username'
        else:
            sql_what = '*'

    if email_only:
        sql_what = 'username'

    additional_sql_where = ''
    if first_char:
        additional_sql_where = ' AND address LIKE %s' % web.sqlquote(first_char.lower() + '%')

    if disabled_only:
        additional_sql_where = ' AND active=0'

    # Get basic profiles
    try:
        if not conn:
            _wrap = SQLWrap()
            conn = _wrap.conn

        if page:
            qr = conn.select('mailbox',
                             vars=sql_vars,
                             what=sql_what,
                             where='domain=$domain %s' % additional_sql_where,
                             order='username ASC',
                             limit=settings.PAGE_SIZE_LIMIT,
                             offset=(page - 1) * settings.PAGE_SIZE_LIMIT)
        else:
            qr = conn.select('mailbox',
                             vars=sql_vars,
                             what=sql_what,
                             where='domain=$domain %s' % additional_sql_where,
                             order='username ASC')

        rows = list(qr)
        if email_only:
            emails = [str(i.username).lower() for i in rows]
            return (True, emails)
        else:
            return (True, rows)
    except Exception as e:
        return (False, repr(e))
