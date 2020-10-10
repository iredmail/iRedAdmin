# Author: Zhang Huangbin <zhb@iredmail.org>

import web

import settings
from libs import iredutils, form_utils
from libs.logger import logger, log_activity

from libs.sqllib import SQLWrap, decorators, sqlutils
from libs.sqllib import general as sql_lib_general

session = web.config.get('_session', {})

# Mail service names manageable in per-domain profile page.
# must sync with
#   - Jinja2 template file: templates/default/macros/general.html
#   - libs/sqllib/domain.py
#   - libs/ldaplib/domain.py
AVAILABLE_DOMAIN_DISABLED_MAIL_SERVICES = [
    'smtp', 'smtpsecured',
    'pop3', 'pop3secured',
    'imap', 'imapsecured',
    'managesieve', 'managesievesecured',
    'sogo',
]


def get_all_domains(conn=None, columns=None, name_only=False):
    """Get all domains. Return (True, [records])."""
    if columns:
        sql_what = ','.join(columns)
    else:
        if name_only:
            sql_what = 'domain'
        else:
            sql_what = '*'

    try:
        if not conn:
            _wrap = SQLWrap()
            conn = _wrap.conn

        result = conn.select('domain', what=sql_what, order='domain ASC')

        if name_only:
            domain_names = [str(r.domain).lower() for r in result]
            return (True, domain_names)
        else:
            return (True, list(result))
    except Exception as e:
        return (False, repr(e))


def get_all_managed_domains(conn=None,
                            columns=None,
                            name_only=False,
                            disabled_only=False):
    """Get all managed domains.

    Returned values:

    - (True, [records])
    - (True, [<domain_name>, <domain_name>, ...])
    - (False, <error>)
    """
    if columns:
        sql_what = ','.join(columns)
    else:
        if name_only:
            sql_what = 'domain.domain'
        else:
            sql_what = 'domain.*'

    sql_where = None
    if disabled_only:
        sql_where = 'domain.active=0'

    try:
        if not conn:
            _wrap = SQLWrap()
            conn = _wrap.conn

        if session.get('is_global_admin'):
            qr = conn.select('domain',
                             what=sql_what,
                             where=sql_where,
                             order='domain ASC')
        else:
            if sql_where:
                sql_where = ' AND ' + sql_where
            qr = conn.select(['domain', 'domain_admins'],
                             vars={'admin': session.username},
                             what=sql_what,
                             where='domain_admins.username=$admin AND domain_admins.domain=domain.domain %s' % sql_where,
                             order='domain.domain ASC')

        if name_only:
            domain_names = [str(r.domain).lower() for r in qr]
            return (True, domain_names)
        else:
            return (True, list(qr))
    except Exception as e:
        return (False, repr(e))


def enable_disable_domains(domains, action, conn=None):
    """Set account status.

    :param domains: a list/tuple/set of mail domain names
    :param action: enable, disable
    :param conn: sql connection cursor
    """
    action = action.lower()
    if action in ['enable', 'active']:
        active = 1

    else:
        active = 0

    try:
        conn.update('domain',
                    vars={'domains': domains},
                    where='domain IN $domains',
                    active=active)

        log_activity(event=action.lower(),
                     msg="{} domain(s): {}.".format(action.title(), ', '.join(domains)))

        return (True, )
    except Exception as e:
        return (False, repr(e))


# Get used quota of domains.
def get_domain_used_quota(conn, domains=None):
    used_quota = {}

    if not domains:
        return used_quota

    domains = [str(d).lower() for d in domains if iredutils.is_domain(d)]
    try:
        qr = conn.select(
            settings.SQL_TBL_USED_QUOTA,
            vars={'domains': domains},
            where='domain IN $domains',
            what='domain,SUM(bytes) AS size, SUM(messages) AS messages',
            group='domain',
            order='domain',
        )

        for r in qr:
            used_quota[str(r.domain)] = {'size': r.size, 'messages': r.messages}
    except:
        pass

    return used_quota


@decorators.require_global_admin
def get_allocated_domain_quota(domain, conn=None):
    num = 0

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    try:
        qr = conn.select('mailbox',
                         vars={'domain': domain},
                         what='SUM(quota) AS total',
                         where='domain = $domain')

        if qr:
            num = int(qr[0].total) or 0
    except:
        pass

    return num


def delete_domains(domains,
                   keep_mailbox_days=0,
                   conn=None):
    domains = [str(d).lower() for d in domains if iredutils.is_domain(d)]
    if not domains:
        return (True, )

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    try:
        keep_mailbox_days = abs(int(keep_mailbox_days))
    except:
        keep_mailbox_days = 0

    if not session.get('is_global_admin'):
        _max_days = max(settings.DAYS_TO_KEEP_REMOVED_MAILBOX)
        if keep_mailbox_days > _max_days:
            # Get the max days
            keep_mailbox_days = _max_days

    # Keep mailboxes 'forever', set to 100 years.
    if keep_mailbox_days == 0:
        sql_keep_days = web.sqlliteral('Null')
    else:
        if settings.backend == 'pgsql':
            sql_keep_days = web.sqlliteral("""CURRENT_TIMESTAMP + INTERVAL '%d DAYS'""" % keep_mailbox_days)
        else:
            # settings.backend == 'mysql'
            sql_keep_days = web.sqlliteral('DATE_ADD(CURDATE(), INTERVAL %d DAY)' % keep_mailbox_days)

    sql_vars = {'domains': domains,
                'admin': session.get('username'),
                'sql_keep_days': sql_keep_days}

    # Log maildir paths of existing users
    try:
        if settings.backend == 'pgsql':
            sql_raw = '''
                INSERT INTO deleted_mailboxes (username, maildir, domain, admin, delete_date)
                SELECT username, \
                       storagebasedirectory || '/' || storagenode || '/' || maildir, \
                       domain, \
                       $admin, \
                       $sql_keep_days
                  FROM mailbox
                 WHERE domain IN $domains'''
        else:
            # settings.backend == 'mysql'
            sql_raw = '''
                INSERT INTO deleted_mailboxes (username, maildir, domain, admin, delete_date)
                SELECT username, \
                       CONCAT(storagebasedirectory, '/', storagenode, '/', maildir) AS maildir, \
                       domain, \
                       $admin, \
                       $sql_keep_days
                  FROM mailbox
                 WHERE domain IN $domains'''

        conn.query(sql_raw, vars=sql_vars)
    except Exception as e:
        logger.error(e)

    try:
        # Delete domain name
        for tbl in ['domain', 'alias', 'domain_admins', 'mailbox',
                    'recipient_bcc_domain', 'recipient_bcc_user',
                    'sender_bcc_domain', 'sender_bcc_user',
                    'forwardings', 'moderators',
                    settings.SQL_TBL_USED_QUOTA]:
            conn.delete(tbl,
                        vars=sql_vars,
                        where='domain IN $domains')

        # Delete alias domain
        conn.delete('alias_domain',
                    vars=sql_vars,
                    where='alias_domain IN $domains OR target_domain IN $domains')

        # Delete domain admins
        for d in domains:
            conn.delete('domain_admins',
                        vars={'domain': '%%@' + d},
                        where='username LIKE $domain')
    except Exception as e:
        return (False, repr(e))

    for d in domains:
        log_activity(event='delete',
                     domain=d,
                     msg="Delete domain: %s." % d)

    return (True, )


@decorators.require_global_admin
def simple_profile(domain, columns=None, conn=None):
    if not iredutils.is_domain(domain):
        return (False, 'INVALID_DOMAIN_NAME')

    sql_what = '*'
    if columns:
        sql_what = ','.join(columns)

    try:
        if not conn:
            _wrap = SQLWrap()
            conn = _wrap.conn

        qr = conn.select('domain',
                         vars={'domain': domain},
                         what=sql_what,
                         where='domain=$domain',
                         limit=1)
        if qr:
            p = list(qr)[0]
            return (True, p)
        else:
            return (False, 'INVALID_DOMAIN_NAME')
    except Exception as e:
        return (False, repr(e))


@decorators.require_global_admin
def profile(domain, conn=None):
    domain = str(domain).lower()

    if not iredutils.is_domain(domain):
        return (False, 'INVALID_DOMAIN_NAME')

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    try:
        # Get domain profile first.
        _qr = simple_profile(domain=domain, conn=conn)
        if _qr[0]:
            _profile = _qr[1]
        else:
            return _qr

        # num_existing_users
        _profile['num_existing_users'] = sql_lib_general.num_users_under_domain(domain=domain, conn=conn)

        return (True, _profile)
    except Exception as e:
        return (False, repr(e))


# Do not apply @decorators.require_global_admin
def get_domain_enabled_services(domain, conn=None):
    qr = sql_lib_general.get_domain_settings(domain=domain, conn=conn)
    if qr[0] is True:
        domain_settings = qr[1]
        enabled_services = domain_settings.get('enabled_services', [])
        return (True, enabled_services)
    else:
        return qr


def add(form, conn=None):
    domain = form_utils.get_domain_name(form)

    # Check domain name.
    if not iredutils.is_domain(domain):
        return (False, 'INVALID_DOMAIN_NAME')

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    # Check whether domain name already exist (domainName, domainAliasName).
    if sql_lib_general.is_domain_exists(domain=domain, conn=conn):
        return (False, 'ALREADY_EXISTS')

    params = {
        'domain': domain,
        'transport': settings.default_mta_transport,
        'active': 1,
        'created': iredutils.get_gmttime(),
    }

    # Name
    kv = form_utils.get_form_dict(form=form, input_name='cn', key_name='description')
    params.update(kv)

    # Add domain in database.
    try:
        conn.insert('domain', **params)
        log_activity(msg="New domain: %s." % (domain),
                     domain=domain,
                     event='create')

        # If it's a normal domain admin with permission to create new domain,
        # assign current admin as admin of this newly created domain.
        if session.get('create_new_domains'):
            qr = assign_admins_to_domain(domain=domain,
                                         admins=[session.get('username')],
                                         conn=conn)
            if not qr[0]:
                return qr

    except Exception as e:
        return (False, repr(e))

    return (True, )


@decorators.require_global_admin
def update(domain, profile_type, form, conn=None):
    profile_type = str(profile_type)
    domain = str(domain).lower()
    sql_vars = {'domain': domain}

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    db_settings = iredutils.get_settings_from_db()

    # Get current domain profile
    qr = simple_profile(conn=conn, domain=domain)
    if qr[0]:
        domain_profile = qr[1]
        domain_settings = sqlutils.account_settings_string_to_dict(domain_profile.get('settings', ''))
        del qr
    else:
        return qr

    # Check disabled domain profiles
    disabled_domain_profiles = []
    if not session.get('is_global_admin'):
        disabled_domain_profiles = domain_settings.get('disabled_domain_profiles', [])
        if profile_type in disabled_domain_profiles:
            return (False, 'PERMISSION_DENIED')

    # Pre-defined update key:value.
    updates = {'modified': iredutils.get_gmttime()}

    if profile_type == 'general':
        # Get name
        cn = form.get('cn', '')
        updates['description'] = cn

        # Get default quota for new user.
        default_user_quota = form_utils.get_single_value(form=form,
                                                         input_name='defaultQuota',
                                                         default_value=0,
                                                         is_integer=True)
        if default_user_quota > 0:
            domain_settings['default_user_quota'] = default_user_quota
        else:
            if 'default_user_quota' in domain_settings:
                domain_settings.pop('default_user_quota')

    elif profile_type == 'advanced':
        # Update min/max password length in domain setting
        if session.get('is_global_admin') or ('password_policies' not in disabled_domain_profiles):
            for (_input_name, _key_name) in [('minPasswordLength', 'min_passwd_length'),
                                             ('maxPasswordLength', 'max_passwd_length')]:
                try:
                    _length = int(form.get(_input_name, 0))
                except:
                    _length = 0

                if _length > 0:
                    if not session.get('is_global_admin'):
                        # Make sure domain setting doesn't exceed global setting.
                        if _input_name == 'minPasswordLength':
                            # Cannot be shorter than global setting.
                            if _length < db_settings['min_passwd_length']:
                                _length = db_settings['min_passwd_length']
                        elif _input_name == 'maxPasswordLength':
                            # Cannot be longer than global setting.
                            if (db_settings['max_passwd_length'] > 0) and \
                               (_length > db_settings['max_passwd_length'] or _length <= db_settings['min_passwd_length']):
                                _length = db_settings['max_passwd_length']

                    domain_settings[_key_name] = _length
                else:
                    if _key_name in domain_settings:
                        domain_settings.pop(_key_name)

        # Update default language for new user
        default_language = form_utils.get_language(form)
        if default_language in iredutils.get_language_maps():
            domain_settings['default_language'] = default_language

        domain_settings['timezone'] = form_utils.get_timezone(form)

    updates['settings'] = sqlutils.account_settings_dict_to_string(domain_settings)
    try:
        conn.update('domain',
                    vars=sql_vars,
                    where='domain=$domain',
                    **updates)

        log_activity(msg="Update domain profile: {} ({}).".format(domain, profile_type),
                     domain=domain,
                     event='update')

        return (True, )
    except Exception as e:
        return (False, repr(e))


def get_paged_domains(first_char=None,
                      cur_page=1,
                      disabled_only=False,
                      conn=None):
    admin = session.get('username')
    page = int(cur_page) or 1

    # A dict used to store domain profiles.
    # Format: {'<domain>': {<key>: <value>, <key>: <value>, ...}}
    records = {}

    try:
        sql_where = ''

        if session.get('is_global_admin'):
            if first_char:
                sql_where = """ domain LIKE %s""" % web.sqlquote(first_char.lower() + '%')

            if disabled_only:
                if sql_where:
                    sql_where += ' AND active=0'
                else:
                    sql_where += ' WHERE active=0'

            if not sql_where:
                sql_where = None

            sql_what = 'domain, description, transport, backupmx, active, aliases, mailboxes, maillists, maxquota, quota'
            qr = conn.select('domain',
                             what=sql_what,
                             where=sql_where,
                             limit=settings.PAGE_SIZE_LIMIT,
                             order='domain',
                             offset=(page - 1) * settings.PAGE_SIZE_LIMIT)

        else:
            sql_where = ' domain.domain = domain_admins.domain AND domain_admins.username = %s' % web.sqlquote(admin)

            if first_char:
                sql_where += """ AND domain.domain LIKE %s""" % web.sqlquote(first_char.lower() + '%')

            if disabled_only:
                if sql_where:
                    sql_where += ' AND domain.active=0'
                else:
                    sql_where += 'domain.active=0'

            sql_what = 'domain.domain, domain.description, domain.transport,'
            sql_what += 'domain.backupmx, domain.active, domain.aliases,'
            sql_what += 'domain.mailboxes, domain.maillists, domain.maxquota,'
            sql_what += 'domain.quota'
            qr = conn.select(['domain', 'domain_admins'],
                             what=sql_what,
                             where=sql_where,
                             limit=settings.PAGE_SIZE_LIMIT,
                             order='domain.domain',
                             offset=(page - 1) * settings.PAGE_SIZE_LIMIT)

        if not qr:
            return (True, {})

        for i in qr:
            _domain = str(i.domain).lower()
            records[_domain] = i

        sql_vars = {'domains': list(records.keys())}

        # Get num_existing_users
        qr = conn.select('mailbox',
                         vars=sql_vars,
                         what='domain, SUM(mailbox.quota) AS quota_count, COUNT(username) AS total',
                         where='domain IN $domains',
                         group='domain',
                         limit=settings.PAGE_SIZE_LIMIT)

        for i in qr:
            _domain = str(i.domain).lower()
            records[_domain]['num_existing_users'] = i.total
            records[_domain]['quota_count'] = i.quota_count

        # Sort domains by domain name
        _domains = list(records.keys())
        _domains.sort()
        _profiles = [records[k] for k in _domains]

        return (True, _profiles)
    except Exception as e:
        return (False, repr(e))


def get_domain_admin_addresses(domain, conn=None):
    """List email addresses of all domain admins (exclude global admins).

    >>> get_domain_admin_addresses(domain='abc.com')
    (True, ['user1@<domain>.com', 'user2@<domain>.com', ...])

    >>> get_domain_admin_addresses(domain='xyz.com')
    (False, '<reason>')
    """
    all_admins = set()
    sql_vars = {'domain': domain}
    try:
        if not conn:
            _wrap = SQLWrap()
            conn = _wrap.conn

        qr = conn.select('domain_admins',
                         vars=sql_vars,
                         what='username',
                         where='domain=$domain')

        for i in qr:
            all_admins.add(str(i.username).lower())

        return (True, list(all_admins))
    except Exception as e:
        return (False, repr(e))


def assign_admins_to_domain(domain, admins, conn=None):
    """Assign list of NEW admins to specified mail domain.

    It doesn't remove existing admins."""
    if not iredutils.is_domain(domain):
        return (False, 'INVALID_DOMAIN_NAME')

    if not isinstance(admins, (list, tuple, set)):
        return (False, 'NO_ADMINS')
    else:
        admins = [str(i).lower() for i in admins if iredutils.is_email(i)]
        if not admins:
            return (False, 'NO_ADMINS')

    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    for adm in admins:
        try:
            conn.insert('domain_admins',
                        domain=domain,
                        username=adm)
        except Exception as e:
            if e.__class__.__name__ == 'IntegrityError':
                pass
            else:
                return (False, repr(e))

    return (True, )


def get_first_char_of_all_domains(conn=None):
    """Get first character of all domains."""
    if not conn:
        _wrap = SQLWrap()
        conn = _wrap.conn

    admin = session.get('username')
    chars = []
    try:
        if sql_lib_general.is_global_admin(admin=admin, conn=conn):
            qr = conn.select('domain',
                             what='SUBSTRING(domain FROM 1 FOR 1) AS first_char',
                             group='first_char')
        else:
            qr = conn.query("""SELECT SUBSTRING(domain.domain FROM 1 FOR 1) AS first_char
                                 FROM domain
                            LEFT JOIN domain_admins ON (domain.domain=domain_admins.domain)
                                WHERE domain_admins.username=$admin
                             GROUP BY first_char""",
                            vars={'admin': admin})

        if qr:
            chars = [i.first_char.upper() for i in qr]
            chars.sort()

        return (True, chars)
    except Exception as e:
        logger.error(e)
        return (False, repr(e))
