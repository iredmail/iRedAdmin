# Author: Zhang Huangbin <zhb@iredmail.org>

import ldap
import web

import settings
from libs import iredutils, iredpwd
from libs.logger import logger, log_traceback
from libs.ldaplib.core import LDAPWrap
from libs.ldaplib import ldaputils, attrs

session = web.config.get('_session')


def is_global_admin(admin, conn=None):
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
            _wrap = LDAPWrap()
            conn = _wrap.conn

        _filter = '(&'
        _filter += '(domainGlobalAdmin=yes)'
        _filter += '(|(objectClass=mailUser)(objectClass=mailAdmin))'
        _filter += '(|(mail={})(shadowAddress={}))'.format(admin, admin)
        _filter += ')'

        qr = conn.search_s(settings.ldap_basedn,
                           ldap.SCOPE_BASE,
                           _filter,
                           ['domainGlobalAdmin'])

        if qr:
            return True
        else:
            return False
    except:
        return False


def is_domain_admin(domain, admin=None, conn=None):
    """Check whether given admin is domain admin. Return True or False."""
    if not admin:
        admin = session.get('username')

    if admin == session.get('username') and session.get('is_global_admin'):
        return True

    try:
        if not conn:
            _wrap = LDAPWrap()
            conn = _wrap.conn

        q_filter = "(&(|(domainName={})(domainAliasName={}))(domainAdmin={}))".format(
            domain,
            domain,
            admin)

        qr = conn.search_s(settings.ldap_basedn,
                           ldap.SCOPE_ONELEVEL,
                           q_filter,
                           ['dn'])

        if qr:
            return True
        else:
            return False
    except:
        return False


# Check whether domain name (either primary domain or alias domain) exists
def is_domain_exists(domain, conn=None):
    # Return True if account is invalid or exist.
    domain = web.safestr(domain).strip().lower()

    if not iredutils.is_domain(domain):
        # Return False if invalid.
        return False

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    query_filter = '(&'
    query_filter += '(objectClass=mailDomain)'
    query_filter += '(|(domainName={})(domainAliasName={}))'.format(domain, domain)
    query_filter += ')'

    # Check domainName and domainAliasName.
    try:
        qr = conn.search_s(settings.ldap_basedn,
                           ldap.SCOPE_ONELEVEL,
                           query_filter,
                           ['dn'])

        if qr:
            # Domain name exist.
            return True
        else:
            return False
    except:
        # Account 'EXISTS' (fake) if lookup failed.
        return True


def check_account_existence(mail, account_type='mail', conn=None):
    """Return tuple `(True,  )` if object exists, `(False, )` if not exists,
    (None, "<reason>") if something wrong happened.

    @param mail: full email address.
    @param account_type: must be one of: mail, user, alias, ml.
    @param conn: ldap connection cursor.
    """
    if account_type not in ['mail', 'user', 'alias', 'ml']:
        return (None, 'INVALID_ACCOUNT_TYPE')

    mail = str(mail).lower()
    mail = iredutils.strip_mail_ext_address(mail)

    if not iredutils.is_email(mail):
        return (None, 'INVALID_MAIL')

    # Filter used to search account.
    _filter = '(&'
    if account_type == 'mail':
        # mail user, mail alias, mailing list, mlmmj mailing list.
        _filter += '(|(objectClass=mailUser)(objectClass=mailList)(objectClass=mailAlias))'
        _filter += '(|(mail={})(shadowAddress={}))'.format(mail, mail)
    elif account_type == 'user':
        # mail user
        _filter += '(objectClass=mailUser)'
        _filter += '(|(mail={})(shadowAddress={}))'.format(mail, mail)

    _filter += ')'

    try:
        if not conn:
            _wrap = LDAPWrap()
            conn = _wrap.conn

        qr = conn.search_s(settings.ldap_basedn,
                           ldap.SCOPE_SUBTREE,
                           _filter,
                           ['dn'])

        if qr:
            return (True, )
        else:
            return (False, )
    except Exception as e:
        # Account 'EXISTS' (fake) if lookup failed.
        logger.error("Error while checking account existence: "
                     "mail={}, account_type={}, "
                     "error={}".format(mail, account_type, e))

        return (None, 'ERROR_WHILE_QUERYING_DB')


def is_email_exists(mail, conn=None):
    qr = check_account_existence(mail=mail, account_type="mail", conn=conn)
    if qr[0]:
        return True
    else:
        return False


# Change password.
def change_password(dn,
                    old_password,
                    new_password,
                    require_cur_passwd=True,
                    conn=None):
    """Change account password.

    If very possible that `old_password` will be set to None/False/<empty>,
    to prevent updating password without old password, we use argument
    `require_old_password=False` instead of use `old_password=None`.
    """

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    try:
        # Reference: RFC3062 - LDAP Password Modify Extended Operation
        if require_cur_passwd:
            conn.passwd_s(dn, old_password, new_password)
        else:
            # Generate password hash and replace value of 'userPassword' attr.
            pw_hash = iredpwd.generate_password_hash(new_password)

            mod_attr = ldaputils.mod_replace('userPassword', pw_hash)
            conn.modify_s(dn, mod_attr)

        return (True, )
    except ldap.UNWILLING_TO_PERFORM:
        return (False, 'INCORRECT_OLDPW')
    except Exception as e:
        return (False, repr(e))


def add_or_remove_attr_values(dn,
                              attr,
                              values,
                              action,
                              ignore_no_such_object=False,
                              conn=None):
    """Add or remove value of attribute which can handle multiple values.

    :param dn: dn of ldap object
    :param attr: ldap attribute name we need to update
    :param values: values of attribute name
    :param action: to add value, use one of: add, assign, enable
                   to delete value, use one of: del, delete, remove, disable
    :param ignore_no_such_object: do nothing if target object doesn't exist.
    :param conn: ldap connection cursor
    """
    if isinstance(values, (list, tuple, set)):
        values = values
    elif values is None:
        values = None
    else:
        values = [values]

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    msg = ''
    if action in ['add', 'assign', 'enable']:
        try:
            _ldif = ldaputils.attr_ldif(attr, values, mode='add')
            conn.modify_s(dn, _ldif)
        except ldap.NO_SUCH_OBJECT:
            if ignore_no_such_object:
                pass
            else:
                return (False, 'NO_SUCH_OBJECT')
        except ldap.TYPE_OR_VALUE_EXISTS:
            pass
        except Exception as e:
            msg = repr(e)
    elif action in ['del', 'delete', 'remove', 'disable']:
        try:
            _ldif = ldaputils.attr_ldif(attr, values, mode='delete')
            conn.modify_s(dn, _ldif)
        except ldap.NO_SUCH_OBJECT:
            pass
        except ldap.NO_SUCH_ATTRIBUTE:
            pass
        except Exception as e:
            msg = repr(e)
    else:
        return (False, 'UNKNOWN_ACTION')

    if not msg:
        return (True, )
    else:
        return (False, msg)


def add_attr_values(dn, attr, values, conn=None):
    return add_or_remove_attr_values(dn=dn,
                                     attr=attr,
                                     values=values,
                                     action='add',
                                     conn=conn)


def remove_attr_values(dn, attr, values, conn=None):
    return add_or_remove_attr_values(dn=dn,
                                     attr=attr,
                                     values=values,
                                     action='remove',
                                     conn=conn)


def replace_attr_value(dn, attr, old_value, new_value, conn=None):
    # Remove old value first
    qr = add_or_remove_attr_values(dn=dn,
                                   attr=attr,
                                   values=[old_value],
                                   action='remove',
                                   conn=conn)
    if not qr[0]:
        return qr

    # Add new value
    qr = add_or_remove_attr_values(dn=dn,
                                   attr=attr,
                                   values=[new_value],
                                   action='add',
                                   conn=conn)

    if not qr[0]:
        return qr

    return (True, )


def add_enabled_services(dn, values, conn=None):
    return add_attr_values(dn=dn,
                           attr='enabledService',
                           values=values,
                           conn=conn)


def remove_enabled_services(dn, values, conn=None):
    return remove_attr_values(dn=dn,
                              attr='enabledService',
                              values=values,
                              conn=conn)


def add_disabled_services(dn, values, conn=None):
    return add_attr_values(dn=dn,
                           attr='disabledService',
                           values=values,
                           conn=conn)


def remove_disabled_services(dn, values, conn=None):
    return remove_attr_values(dn=dn,
                              attr='disabledService',
                              values=values,
                              conn=conn)


# Update value of attribute which must be single value.
def update_attr_with_single_value(dn, attr, value, conn=None):
    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    if isinstance(value, list):
        pass
    elif isinstance(value, (tuple, set)):
        value = list(value)
    elif isinstance(value, int):
        value = [str(value)]
    else:
        value = [str(value)]

    try:
        mod_attr = ldaputils.mod_replace(attr, value)
        conn.modify_s(dn, mod_attr)
        return (True, )
    except ldap.NO_SUCH_OBJECT:
        return (False, 'NO_SUCH_ACCOUNT')
    except Exception as e:
        return (False, repr(e))


def __reset_num_domain_current_accounts(domain, num, account_type='user', conn=None):
    """Update number of existing accounts in domain profile."""
    dn = ldaputils.rdn_value_to_domain_dn(domain)
    if not isinstance(num, int):
        return (False, 'INVALID_NUMBER')

    if num < 0:
        num = 0

    mapping = {'user': 'domainCurrentUserNumber',
               'alias': 'domainCurrentAliasNumber',
               'maillist': 'domainCurrentListNumber'}
    attr_count = mapping[account_type]

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    qr = update_attr_with_single_value(dn=dn,
                                       attr=attr_count,
                                       value=num,
                                       conn=conn)

    return qr


def reset_num_domain_current_users(domain, num, conn=None):
    return __reset_num_domain_current_accounts(domain=domain,
                                               num=num,
                                               account_type='user',
                                               conn=conn)


def __update_num_domain_current_accounts(domain,
                                         increase=False,
                                         decrease=False,
                                         step_number=1,
                                         account_type='user',
                                         conn=None):
    """Increase or decrease number of existing accounts in domain profile."""
    if not isinstance(step_number, int):
        step_number = 1

    if step_number <= 0:
        step_number = 1

    attr_map = {
        'user': 'domainCurrentUserNumber',
        'alias': 'domainCurrentAliasNumber',
        'maillist': 'domainCurrentListNumber',
    }
    attr_count = attr_map[account_type]

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    dn = ldaputils.rdn_value_to_domain_dn(domain)

    # Get domain profile first
    try:
        qr = conn.search_s(dn,
                           ldap.SCOPE_BASE,
                           '(&(objectClass=mailDomain)(domainName=%s))' % domain,
                           [attr_count])

    except Exception as e:
        log_traceback()
        return (False, repr(e))

    if qr:
        _ldif = iredutils.bytes2str(qr[0][1])
        _current = int(_ldif.get(attr_count, [0])[0])

        _num = _current
        if increase:
            _num = _current + step_number
        elif decrease:
            _num = _current - step_number

        if _num < 0:
            _num = 0

        # Update count
        update_attr_with_single_value(dn=dn,
                                      attr=attr_count,
                                      value=_num,
                                      conn=conn)

    return (True, )


def update_num_domain_current_users(domain,
                                    increase=False,
                                    decrease=False,
                                    step_number=1,
                                    conn=None):
    return __update_num_domain_current_accounts(domain=domain,
                                                increase=increase,
                                                decrease=decrease,
                                                step_number=step_number,
                                                account_type='user',
                                                conn=conn)


def enable_disable_account_by_dn(dn, action, conn=None):
    """Update LDAP attribute value 'accountStatus' to 'active' or 'disabled'.

    :param dn: full dn of the account
    :param action: enable, disable.
    :param conn: ldap connection cursor
    """
    # Set value of valid account status.
    if action == 'enable':
        _status = 'active'
    else:
        _status = 'disabled'

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    qr = update_attr_with_single_value(dn=dn,
                                       attr='accountStatus',
                                       value=_status,
                                       conn=conn)

    return qr


def enable_disable_mail_accounts(mails, account_type, action, conn=None):
    """Enable (action='enable') or disable (action='disable') given mail users.

    :param mails: a list/tuple/set of user mail addresses
    :param account_type: user, maillist, alias.
    :param action: enable, disable.
    :param conn: ldap connection cursor
    """
    mails = [str(v).lower() for v in mails if iredutils.is_email(v)]

    action = action.lower()
    if action not in ['enable', 'disable']:
        return (False, 'INVALID_ACTION')

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    mapping = {'user': ldaputils.rdn_value_to_user_dn}

    for mail in mails:
        _func = mapping[account_type]
        dn = _func(mail)

        qr = enable_disable_account_by_dn(dn=dn,
                                          action=action,
                                          conn=conn)
        if not qr[0]:
            return qr

    return (True, )


def enable_disable_users(mails, action, conn=None):
    return enable_disable_mail_accounts(mails=mails, account_type='user', action=action, conn=conn)


def enable_disable_admins(mails, action, conn=None):
    """Enable (action='enable') or disable (action='disable') given mail admins.

    :param mails: a list/tuple/set of mail addresses of mail admin accounts
    :param action: enable, disable.
    :param conn: ldap connection cursor
    """
    mails = [str(v).lower() for v in mails if iredutils.is_email(v)]
    action = action.lower()
    if action not in ['enable', 'disable']:
        return (False, 'INVALID_ACTION')

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    for mail in mails:
        # Standalone admin account
        dn = ldaputils.rdn_value_to_admin_dn(mail)
        qr = enable_disable_account_by_dn(dn=dn,
                                          action=action,
                                          conn=conn)

        if not qr[0]:
            if qr[0] == 'NO_SUCH_ACCOUNT':
                # Admin is a normal mail user.
                dn = ldaputils.rdn_value_to_user_dn(mail)
                add_or_remove_attr_values(dn=dn,
                                          attr='enabledService',
                                          values='domainadmin',
                                          action=action,
                                          conn=conn)

                add_or_remove_attr_values(dn=dn,
                                          attr='domainGlobalAdmin',
                                          values='yes',
                                          action=action,
                                          conn=conn)

    return (True, )


def __num_accounts_under_domain(domain,
                                account_type='user',
                                disabled_only=False,
                                first_char=None,
                                update_statistics=False,
                                conn=None):
    """Get number of accounts under specified domain.

    :param domain: domain name you want to query.
    :param account_type: one of 'user', 'list', 'alias', 'ml', 'mixed_ml'.
    :param conn: ldap connection cursor.
    """
    domain = str(domain).lower()
    if not iredutils.is_domain(domain):
        return (False, 'INVALID_DOMAIN_NAME')

    dn_domain = ldaputils.rdn_value_to_domain_dn(domain)

    statistics_attr = None
    if account_type == 'user':
        search_filter = '(&(objectClass=mailUser)(!(mail=@%s)))' % domain
        statistics_attr = 'domainCurrentUserNumber'
    else:
        search_filter = '(&(objectClass=mailUser)(!(mail=@%s)))' % domain

    if disabled_only:
        search_filter = '(&' + search_filter + '(accountStatus=disabled)' + ')'

    if first_char:
        search_filter = '(&' + search_filter + '(|(cn=%s*)(mail=%s*))' + ')'

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    try:
        qr = conn.search_s(dn_domain,
                           ldap.SCOPE_SUBTREE,
                           search_filter,
                           ['dn'])

        num = len(qr)

        if update_statistics and statistics_attr:
            mod_attr = ldaputils.mod_replace(statistics_attr, num)
            try:
                conn.modify_s(dn_domain, mod_attr)
            except:
                log_traceback()

        return num
    except:
        log_traceback()
        return 0


def num_users_under_domain(domain, update_statistics=False, conn=None):
    return __num_accounts_under_domain(domain=domain,
                                       account_type='user',
                                       update_statistics=update_statistics,
                                       conn=conn)


# List all domains.
def get_all_domains(attributes=None,
                    search_filter=None,
                    names_only=False,
                    disabled_only=False,
                    starts_with=None,
                    conn=None):
    admin = session['username']

    if not attributes:
        attributes = list(attrs.DOMAIN_SEARCH_ATTRS)

    if not search_filter:
        search_filter = '(&(objectClass=mailDomain)(domainAdmin=%s))' % (admin)
        if session.get('is_global_admin'):
            search_filter = '(objectClass=mailDomain)'

    if disabled_only is True:
        # use "is True" here to prevent client input invalid value in url.
        search_filter = '(&' + search_filter + '(accountStatus=disabled)' + ')'

    if starts_with:
        if iredutils.is_valid_account_first_char(starts_with):
            search_filter = '(&' + search_filter + ('(domainName=%s*)' % starts_with) + ')'

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    try:
        qr = conn.search_s(settings.ldap_basedn,
                           ldap.SCOPE_ONELEVEL,
                           search_filter,
                           attributes)
        if names_only:
            domain_names = []
            for (_dn, _ldif) in qr:
                _ldif = iredutils.bytes2str(_ldif)
                domain_names += _ldif['domainName']

            return (True, domain_names)
        else:
            return (True, iredutils.bytes2str(qr))
    except Exception as e:
        return (False, repr(e))


def get_domain_password_lengths(domain,
                                account_settings=None,
                                fallback_to_global_settings=False,
                                db_settings=None,
                                conn=None):
    das = {}

    if account_settings:
        das = account_settings
    else:
        if not conn:
            _wrap = LDAPWrap()
            conn = _wrap.conn

        dn = ldaputils.rdn_value_to_domain_dn(domain)
        _filter = '(&(objectClass=mailDomain)(|(domainName={})(domainAliasName={})))'.format(domain, domain)

        _qr = conn.search_s(dn,
                            ldap.SCOPE_BASE,
                            _filter,
                            ['domainName', 'accountSetting'])
        if _qr:
            das = ldaputils.get_account_settings_from_qr(_qr).get(domain, {})

    min_pw_len = das.get('minPasswordLength', 0)
    max_pw_len = das.get('maxPasswordLength', 0)

    if fallback_to_global_settings:
        if not db_settings:
            db_settings = iredutils.get_settings_from_db(params=['min_passwd_length', 'max_passwd_length'])

        if min_pw_len < db_settings['min_passwd_length']:
            min_pw_len = db_settings['min_passwd_length']

        if max_pw_len < db_settings['max_passwd_length']:
            max_pw_len = db_settings['max_passwd_length']

    return (min_pw_len, max_pw_len)


def get_paged_account_list(account_profiles,
                           current_page=1,
                           domain=None,
                           account_type=None,
                           order_name=None,
                           order_by_desc=False,
                           size_limit=None,
                           conn=None):
    """Sort accounts. Return a dict which contains keys:

    - total : number of total accounts
    - account_profiles: list of ldap query result sets ((<dn>: {...}) tuples)
    - pages: number of total pages show be showed in account list page.

    @account_profiles -- list of account_profiles (with many account details)
    @current_page -- offset page
    @domain -- accounts are under this domain
    @account_type -- account type
    @order_name -- order result set by given attribute.
    @order_by_desc -- order result set descending (desc)
    @size_limit -- show how many accounts in one page
    """
    if not size_limit:
        size_limit = settings.PAGE_SIZE_LIMIT

    current_page = int(current_page)

    # Initial a dict to set default values.
    result = {
        'total': 0,
        'account_profiles': [],
        'pages': 0,
    }

    # Get total accounts.
    total = len(account_profiles)
    result['total'] = total

    # Get number of actual pages.
    if total % size_limit == 0:
        pages = total / size_limit
    else:
        pages = (total / size_limit) + 1

    result['pages'] = pages

    if current_page >= pages:
        current_page = pages

    _total_quota = 0
    if (account_type == 'user') and domain:
        if order_name == 'quota':
            # sort accounts by real-time quota usage
            _all_used_quota = get_all_account_used_quota_under_domain(domain)
            _dict_all_used_quota = {}
            for _uq in _all_used_quota:
                _dict_all_used_quota[str(_uq.username)] = _uq.bytes

            del _all_used_quota

            # Generate new list to store quota <-> user map
            tmp_map = []
            for act in account_profiles:
                _ldif = iredutils.bytes2str(act[1])
                _mail = _ldif['mail'][0].lower()
                _quota = int(_ldif.get('mailQuota', [0])[0])

                if _quota > 0:
                    _used_quota = _dict_all_used_quota.get(_mail, 0)
                    _mailbox_usage_percent = '%2f' % (float(_used_quota) / _quota)
                else:
                    _mailbox_usage_percent = 0

                tmp_map.append((_mailbox_usage_percent, act))

                # Update total quota size
                _total_quota += _quota

            del _dict_all_used_quota

            if order_by_desc:
                tmp_map.sort(reverse=True)
            else:
                tmp_map.sort()

            account_profiles = [r[1] for r in tmp_map]
            del tmp_map

        elif order_name == 'name':
            # Generate new list to store name <-> user map
            tmp_map = []
            for act in account_profiles:
                (_dn, _ldif) = act
                _mail = _ldif['mail'][0]
                _name = _ldif.get('cn', [None])[0]
                if not _name:
                    # If no display name, use username part of email address instead.
                    _name = _mail.split('@', 1)[0]

                tmp_map.append((_name, act))

            if order_by_desc:
                tmp_map.sort(reverse=True)
            else:
                tmp_map.sort()

            account_profiles = [r[1] for r in tmp_map]
            del tmp_map
    else:
        # Sort accounts in place.
        account_profiles.sort()

    # Get account list used to display in current page.
    if size_limit < total < ((current_page - 1) * size_limit):
        result['account_profiles'] = account_profiles[-1:-size_limit]
    else:
        result['account_profiles'] = account_profiles[int((current_page - 1) * size_limit): int((current_page - 1) * size_limit + size_limit)]

    # Get total domain mailbox quota
    if account_type == 'user':
        if order_name == 'quota' and domain:
            pass
        else:
            counter = 0
            for i in account_profiles:
                # Get total quota of this domain
                quota = i[1].get('mailQuota', ['0'])[0]
                if quota.isdigit():
                    _total_quota += int(quota)
                    counter += 1

        # Update number of current domain quota size in LDAP (@attrs.ATTR_DOMAIN_CURRENT_QUOTA_SIZE).
        if domain:
            # Update number of current domain quota size in LDAP.
            dn_domain = ldaputils.rdn_value_to_domain_dn(domain)
            update_attr_with_single_value(dn=dn_domain,
                                          attr=attrs.ATTR_DOMAIN_CURRENT_QUOTA_SIZE,
                                          value=str(_total_quota),
                                          conn=conn)

    return result


def get_allocated_domain_quota(domain, conn=None):
    domain = web.safestr(domain).strip().lower()

    if not iredutils.is_domain(domain):
        return (False, 'INVALID_DOMAIN_NAME')

    dn = ldaputils.rdn_value_to_domain_dn(domain)

    allocated_quota = 0

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    try:
        # Use '(!(mail=@domain.com))' to exclude catch-all account.
        qr = conn.search_s(attrs.DN_BETWEEN_USER_AND_DOMAIN + dn,
                           ldap.SCOPE_SUBTREE,
                           '(objectClass=mailUser)',
                           ['mailQuota'])

        for (_dn, _ldif) in qr:
            _ldif = iredutils.bytes2str(_ldif)
            quota = _ldif.get('mailQuota', ['0'])[0]
            if quota.isdigit():
                allocated_quota += int(quota)

        return (True, allocated_quota)
    except ldap.NO_SUCH_OBJECT:
        return (False, 'NO_SUCH_ACCOUNT')
    except ldap.SIZELIMIT_EXCEEDED:
        return (False, 'EXCEEDED_LDAP_SERVER_SIZELIMIT')
    except Exception as e:
        return (False, repr(e))


def get_domain_used_quota(domains=None):
    """Get real-time used quota of given domains."""
    if not domains:
        return {}

    domains = [str(d).lower() for d in domains if iredutils.is_domain(d)]
    try:
        qr = web.conn_iredadmin.select(
            settings.SQL_TBL_USED_QUOTA,
            vars={'domains': domains},
            where='domain IN $domains',
            what='domain,SUM(bytes) AS size, SUM(messages) AS messages',
            group='domain',
            order='domain',
        )

        d = {}
        for i in qr:
            d[str(i.domain)] = {'size': i.size, 'messages': i.messages}

        return d
    except:
        return {}


def get_account_used_quota(accounts):
    # @accounts: must be list/tuple of email addresses.

    # Pre-defined dict of used quotas.
    #   {'user@domain.com': {'bytes': INTEGER, 'messages': INTEGER,}}
    if not accounts:
        return {}

    d = {}

    try:
        qr = web.conn_iredadmin.select(
            settings.SQL_TBL_USED_QUOTA,
            vars={'accounts': accounts},
            where='username IN $accounts',
            what='username, bytes, messages',
        )

        for row in qr:
            d[row.get('username')] = {'bytes': row.get('bytes', 0),
                                      'messages': row.get('messages', 0)}
    except:
        pass

    return d


def get_all_account_used_quota_under_domain(domain):
    # return list of dicts
    if not iredutils.is_domain(domain):
        return []

    try:
        qr = web.conn_iredadmin.select(
            settings.SQL_TBL_USED_QUOTA,
            where='domain=%s' % web.sqlquote(domain),
            what='username,bytes,messages',
        )
        return list(qr)
    except:
        return []


def delete_account_used_quota(accounts):
    # @accounts: must be list/tuple of email addresses.
    if not isinstance(accounts, (list, tuple)):
        return (False, 'INVALID_MAIL')

    if accounts:
        try:
            web.conn_iredadmin.delete(
                settings.SQL_TBL_USED_QUOTA,
                vars={'accounts': accounts},
                where='username IN $accounts',
            )
            return (True, )
        except Exception as e:
            return (False, repr(e))
    else:
        return (True, )


def get_next_uid_gid(conn):
    next_uid = settings.MIN_UID
    next_gid = settings.MIN_GID

    # Get all assigned uid/gid
    exist_uids = []
    exist_gids = []

    qr = conn.search_s(settings.ldap_basedn,
                       ldap.SCOPE_SUBTREE,
                       '(objectClass=*)',
                       ['uidNumber', 'gidNumber'])

    if qr:
        for (_dn, _ldif) in qr:
            _ldif = iredutils.bytes2str(_ldif)

            if 'uidNumber' in _ldif:
                exist_uids.append(int(_ldif['uidNumber'][0]))

            if 'gidNumber' in _ldif:
                exist_gids.append(int(_ldif['gidNumber'][0]))

    del qr

    if exist_uids:
        exist_uids.sort()
        max_uid = list(exist_uids)[-1]
        if max_uid >= next_uid:
            next_uid = max_uid + 1

    if exist_gids:
        exist_gids.sort()
        max_gid = list(exist_gids)[-1]
        if max_gid >= next_gid:
            next_gid = max_gid + 1

    return {'next_uid': next_uid, 'next_gid': next_gid}


def filter_existing_domains(domains, conn=None):
    """
    Remove non-existing domains from given list of domains , return a
    dict of existing ones and non-existing ones.

    :param domains: list of domain names
    :param conn: ldap connection cursor
    """
    domains = list({str(v).lower() for v in domains if iredutils.is_domain(v)})

    exist = []
    nonexist = []

    if not domains:
        return {'exist': exist, 'nonexist': nonexist}

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    _filter = '(&(objectClass=mailDomain)'
    _filter += '(|'
    for d in domains:
        _filter += '(domainName={})(domainAliasName={})'.format(d, d)

    _filter += '))'

    try:
        qr = conn.search_s(settings.ldap_basedn,
                           ldap.SCOPE_ONELEVEL,
                           _filter,
                           ['domainName', 'domainAliasName'])

        if not qr:
            # All are not exist
            nonexist = domains
        else:
            for (_dn, _ldif) in qr:
                _ldif = iredutils.bytes2str(_ldif)
                exist += _ldif.get('domainName', []) + _ldif.get('domainAliasName', [])

            nonexist = [v for v in domains if v not in exist]
    except:
        log_traceback()

    return {'exist': exist, 'nonexist': nonexist}


def exclude_non_existing_emails_in_domain(domain, mails, conn=None):
    """
    Remove non-existing addresses in specified domain from given list of mail
    addresses. Return a list of existing and external addresses.

    :param domain: mail domain name.
    :param mails: a list/set/tuple of email addresses
    :param conn: ldap connection cursor
    """
    domain = domain.lower()
    mails = {str(v).lower()
             for v in mails
             if iredutils.is_email(v)}

    _internals = {i for i in mails if i.endswith('@' + domain)}
    _externals = {i for i in mails if not i.endswith('@' + domain)}

    dn = ldaputils.rdn_value_to_domain_dn(domain)
    qr = filter_existing_emails(mails=_internals, base_dn=dn, conn=conn)
    return list(_externals) + qr['exist']


def filter_existing_emails(mails, base_dn=None, conn=None):
    """
    Remove non-existing addresses from given list of mail addresses, return a
    list of existing ones.

    :param mails: list of email addresses
    :param base_dn: if not present, search from `settings.ldap_basedn`
    :param conn: ldap connection cursor
    """
    mails = [str(v).lower()
             for v in mails
             if iredutils.is_email(v)]
    mails = list(set(mails))

    result = {'exist': [], 'nonexist': []}

    if not mails:
        return result

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    _filter = '(&'
    _filter += '(|(objectClass=mailUser)(objectClass=mailList)(objectClass=mailAlias))'
    _filter += '(|'
    for addr in mails:
        _filter += '(mail={})(shadowAddress={})'.format(addr, addr)

    _filter += '))'

    if not base_dn:
        base_dn = settings.ldap_basedn

    try:
        qr = conn.search_s(base_dn,
                           ldap.SCOPE_SUBTREE,
                           _filter,
                           ['mail', 'shadowAddress'])

        if not qr:
            # None of them exists.
            result['nonexist'] = mails
        else:
            for (_dn, _ldif) in qr:
                _ldif = iredutils.bytes2str(_ldif)
                result['exist'] += _ldif.get('mail', []) + _ldif.get('shadowAddress', [])

            result['nonexist'] = [v for v in mails if v not in result['exist']]

        # Remove duplicates and sort.
        result['exist'] = list(set(result['exist']))
        result['nonexist'] = list(set(result['nonexist']))
    except:
        log_traceback()

    return result


def get_profile_by_dn(dn, query_filter=None, attributes=None, conn=None):
    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    if not attributes:
        attributes = ['*']

    if not filter:
        query_filter = "(objectClass=*)"

    try:
        # Query standalone admin account
        qr = conn.search_s(dn,
                           ldap.SCOPE_BASE,
                           query_filter,
                           attributes)

        if qr:
            (_dn, _ldif) = qr[0]
            _ldif = iredutils.bytes2str(_ldif)
            return (True, {'dn': _dn, 'ldif': _ldif})
        else:
            return (False, 'NO_SUCH_ACCOUNT')
    except ldap.NO_SUCH_OBJECT:
        return (False, 'NO_SUCH_ACCOUNT')
    except Exception as e:
        return (False, repr(e))


def __get_account_setting_by_dn(dn,
                                query_filter=None,
                                profile=None,
                                conn=None):
    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    if not profile:
        qr = get_profile_by_dn(dn=dn,
                               query_filter=query_filter,
                               attributes=['accountSetting'],
                               conn=conn)

        if not qr[0]:
            return qr

        profile = qr[1]['ldif']

    _as_list = profile.get('accountSetting', [])
    _as_dict = ldaputils.account_setting_list_to_dict(_as_list)
    return (True, _as_dict)


def get_admin_account_setting(mail, profile=None, conn=None):
    """Get per-admin account settings from account profile (dict of LDIF data).

    :param mail: email address of domain admin
    :param profile: dict of admin profile LDIF data
    :param conn: ldap connection cursor
    """
    mail = str(mail).lower()
    if not iredutils.is_email(mail):
        return (False, 'INVALID_MAIL')

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    if profile:
        _as = ldaputils.get_account_setting_from_profile(profile)
        return (True, _as)
    else:
        # Query standalone admin account first
        dn = ldaputils.rdn_value_to_admin_dn(mail)
        _filter = '(&(objectClass=mailAdmin)(mail=%s))' % mail
        qr = __get_account_setting_by_dn(dn=dn,
                                         query_filter=_filter,
                                         conn=conn)

        if not qr[0]:
            # Query mail user
            dn = ldaputils.rdn_value_to_user_dn(mail)
            _filter = '(&(objectClass=mailUser)(|(enabledService=domainadmin)(domainGlobalAdmin=yes)))'
            qr = __get_account_setting_by_dn(dn=dn,
                                             query_filter=_filter,
                                             conn=conn)
            if not qr[0]:
                return qr

        return (True, qr[1])


def get_domain_account_setting(domain, profile=None, conn=None):
    domain = str(domain).lower()
    if not iredutils.is_domain(domain):
        return (False, 'INVALID_DOMAIN_NAME')

    if profile:
        dn = None
    else:
        dn = ldaputils.rdn_value_to_domain_dn(domain)

    return __get_account_setting_by_dn(dn=dn, profile=profile, conn=conn)


def get_user_account_setting(mail, profile=None, conn=None):
    mail = str(mail).lower()
    if not iredutils.is_email(mail):
        return (False, 'INVALID_MAIL')

    if profile:
        dn = None
    else:
        dn = ldaputils.rdn_value_to_user_dn(mail)

    return __get_account_setting_by_dn(dn=dn, profile=profile, conn=conn)


def delete_ldap_tree(dn, conn=None):
    """Recursively delete entries under given dn (given dn will be removed too)."""
    errors = {}
    try:
        if not conn:
            _wrap = LDAPWrap()
            conn = _wrap.conn

        qr = conn.search_s(dn,
                           ldap.SCOPE_ONELEVEL,
                           '(objectClass=*)',
                           ['hasSubordinates'])

        dn_without_leaf = []
        dn_with_leaf = []
        for (_dn, _ldif) in qr:
            _ldif = iredutils.bytes2str(_ldif)
            if _ldif['hasSubordinates'][0] == 'TRUE':
                dn_with_leaf.append(_dn)
            else:
                dn_without_leaf.append(_dn)

        if dn_without_leaf:
            for _dn in dn_without_leaf:
                try:
                    conn.delete_s(_dn)
                except Exception as e:
                    errors[_dn] = repr(e)

        for _dn in dn_with_leaf:
            delete_ldap_tree(_dn, conn=conn)

        conn.delete_s(dn)
    except ldap.NO_SUCH_OBJECT:
        pass
    except Exception as e:
        errors[dn] = repr(e)

    if errors:
        return (False, repr(errors))
    else:
        return (True, )


def get_first_char_of_all_accounts(domain, account_type, conn=None):
    """Get a list of first character of mail addresses under given domain.

    @domain - must be a valid domain name.
    @account_type - must be one of: user, maillist, ml, alias.
    @conn - ldap connection cursor.
    """
    if not iredutils.is_domain(domain):
        return []

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    if account_type == 'user':
        _filter = '(objectClass=mailUser)'
        _dn = ldaputils.rdn_value_to_ou_users_dn(domain)
    else:
        return []

    chars = set()
    try:
        qr = conn.search_s(_dn,
                           ldap.SCOPE_ONELEVEL,
                           _filter,
                           ['mail'])

        for (_dn, _ldif) in qr:
            _ldif = iredutils.bytes2str(_ldif)
            _char = _ldif['mail'][0][0]
            chars.add(_char.upper())

        chars = list(chars)
        chars.sort()
    except:
        log_traceback()

    return chars
