# Author: Zhang Huangbin <zhb@iredmail.org>

import time
import ldap
import web
import settings
from libs import iredutils, form_utils
from libs.logger import log_traceback, log_activity

from libs.ldaplib.core import LDAPWrap
from libs.ldaplib import attrs, iredldif, ldaputils, decorators
from libs.ldaplib import admin as ldap_lib_admin
from libs.ldaplib import general as ldap_lib_general

session = web.config.get('_session')


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


def get_first_char_of_all_domains(conn=None):
    """Get a list of first character of all domains."""
    chars = set()
    qr = ldap_lib_admin.get_managed_domains(admin=session.get('username'),
                                            attributes=['domainName'],
                                            conn=conn)
    if qr[0]:
        _domains = qr[1]
        for d in _domains:
            chars.add(d[0].upper())

        chars = list(chars)
        chars.sort()

        return (True, chars)
    else:
        return qr


def get_profile(domain,
                attributes=None,
                convert_account_settings_to_dict=False,
                conn=None):
    """Get domain profile."""
    domain = str(domain).lower()

    if not attributes:
        attributes = list(attrs.DOMAIN_ATTRS_ALL)

    try:
        dn = ldaputils.rdn_value_to_domain_dn(domain)
        _filter = '(&(objectClass=mailDomain)(|(domainName={})(domainAliasName={})))'.format(domain, domain)

        qr = ldap_lib_general.get_profile_by_dn(dn=dn,
                                                query_filter=_filter,
                                                attributes=attributes,
                                                conn=conn)

        if not qr[0]:
            return qr

        _dn = qr[1]['dn']
        _ldif = qr[1]['ldif']

        # Convert accountSetting to a dict
        if convert_account_settings_to_dict:
            _as = _ldif.get('accountSetting', [])
            if _as:
                _as_dict = ldaputils.account_setting_list_to_dict(_as)
                _ldif['accountSetting'] = _as_dict

        return (True, {'dn': _dn, 'ldif': _ldif})
    except ldap.NO_SUCH_OBJECT:
        return (False, 'INVALID_DOMAIN_NAME')
    except Exception as e:
        return (False, repr(e))


def get_profiles_of_managed_domains(attributes=None,
                                    name_only=False,
                                    disabled_only=False,
                                    convert_account_settings_to_dict=False,
                                    conn=None):
    """Get profiles of all managed domains."""
    if name_only:
        attributes = ['domainName']
    else:
        if not attributes:
            attributes = list(attrs.DOMAIN_ATTRS_ALL)

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    # Construct ldap filter
    if session.get('is_global_admin'):
        qf = '(objectClass=mailDomain)'
    else:
        qf = '(&(objectClass=mailDomain)(domainAdmin=%s))' % session.username

    if disabled_only:
        qf = '(&' + qf + '(accountStatus=disabled)' + ')'

    try:
        profiles = {}
        domains = []

        qr = conn.search_s(settings.ldap_basedn,
                           ldap.SCOPE_ONELEVEL,
                           qf,
                           attributes)

        for (_dn, _ldif) in qr:
            _ldif = iredutils.bytes2str(_ldif)
            _domain = _ldif['domainName'][0]

            if name_only:
                domains.append(_domain)
            else:
                # Convert accountSetting to a dict
                if convert_account_settings_to_dict:
                    _as = _ldif.get('accountSetting', [])
                    if _as:
                        _as_dict = ldaputils.account_setting_list_to_dict(_as)
                        _ldif['accountSetting'] = _as_dict

                profiles[_domain] = _ldif

        if name_only:
            return (True, domains)
        else:
            return (True, profiles)
    except Exception as e:
        return (False, repr(e))


@decorators.require_global_admin
def update_domain_status_for_all_accounts(domain, status='active', conn=None):
    """Add or remove 'domainStatus=disabled' in all mail accounts.

    @domain -- the domain name
    @status -- domain status: active, disabled
    @conn -- ldap connection cursor
    """
    domain = str(domain).lower()
    dn = ldaputils.rdn_value_to_domain_dn(domain)

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    # Construct ldap query filter
    _qf_objs = '(|(objectClass=mailUser)(objectClass=mailList)(objectClass=mailAlias)(objectClass=mailExternalUser))'
    if status == 'active':
        _qf_status = "(domainStatus=disabled)"

        # Remove `domainStatus`
        mod_attr = ldaputils.mod_replace('domainStatus', None)
    else:
        _qf_status = "(!(domainStatus=disabled))"

        # Add `domainStatus=disabled`
        mod_attr = ldaputils.mod_replace('domainStatus', 'disabled')

    qf = '(&' + _qf_objs + _qf_status + ')'

    try:
        qr = conn.search_s(dn,
                           ldap.SCOPE_SUBTREE,
                           qf,
                           ['dn'])

        for (dn, _) in qr:
            try:
                conn.modify_s(dn, mod_attr)
            except:
                log_traceback()

        return (True, )
    except Exception as e:
        return (False, repr(e))


def enable_disable_domains(domains, action, conn=None):
    """Enable or disable specified domains.

    :param domains: a list/tuple/set which contains domain names
    :param action: active, disable. ('enable', 'disable' are allowed too)
    :param conn: ldap connection cursor
    """
    if not (domains and isinstance(domains, (list, tuple, set))):
        return (False, 'NO_DOMAIN_SELECTED')

    domains = [str(d).lower() for d in domains if iredutils.is_domain(d)]
    if not domains:
        return (True, )

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    result = {}
    for domain in domains:
        dn = ldaputils.rdn_value_to_domain_dn(domain)

        try:
            ldap_lib_general.enable_disable_account_by_dn(dn=dn,
                                                          action=action,
                                                          conn=conn)

            if action in ['active', 'enable']:
                update_domain_status_for_all_accounts(domain=domain, status='active', conn=conn)
            elif action in ['disable', 'disabled']:
                update_domain_status_for_all_accounts(domain=domain, status='disabled', conn=conn)

        except Exception as e:
            result[domain] = repr(e)

    if result == {}:
        return (True, )
    else:
        return (False, repr(result))


# Get domain default user quota: domainDefaultUserQuota.
# - domainAccountSetting must be a dict.
def get_default_user_quota(domain, domain_account_setting=None, conn=None):
    # Return 0 as unlimited.
    domain = web.safestr(domain).lower()
    dn = ldaputils.rdn_value_to_domain_dn(domain)

    if domain_account_setting:
        # Get from accountSetting directly
        if 'defaultQuota' in domain_account_setting:
            return int(domain_account_setting['defaultQuota'])
        else:
            return 0
    else:
        # Query ldap to get the setting
        try:
            if not conn:
                _wrap = LDAPWrap()
                conn = _wrap.conn

            qr = conn.search_s(dn,
                               ldap.SCOPE_BASE,
                               '(domainName=%s)' % domain,
                               ['domainName', 'accountSetting'])

            account_settings = ldaputils.get_account_settings_from_qr(qr)

            if 'defaultQuota' in account_settings[domain]:
                return int(account_settings[domain]['defaultQuota'])
            else:
                return 0
        except Exception:
            return 0


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
        _wrap = LDAPWrap()
        conn = _wrap.conn

    dn = ldaputils.rdn_value_to_domain_dn(domain)

    qr = ldap_lib_general.add_attr_values(dn=dn,
                                          attr='domainAdmin',
                                          values=[admins],
                                          conn=conn)

    return qr


def list_accounts(attributes=None,
                  search_filter=None,
                  names_only=False,
                  disabled_only=False,
                  starts_with=None,
                  conn=None):
    """List all domains under control.

    @attributes -- list of ldap attribute names should be queried.
    @search_filter -- ldap search filter used to query domain.
    @names_only -- [True | False]. Return a list of mail domain names.
    @disabled_only -- [True | False]. Just query disabled domains.
    @starts_with -- a character. Just query mail domain names which starts with
                    given character.
    @conn -- ldap connection cursor
    """
    qr = ldap_lib_general.get_all_domains(attributes=attributes,
                                          search_filter=search_filter,
                                          names_only=names_only,
                                          disabled_only=disabled_only,
                                          starts_with=starts_with,
                                          conn=conn)

    if qr[0]:
        all_domains = qr[1]
        all_domains.sort()
        return (True, all_domains)
    else:
        return qr


def add(form, conn=None):
    """Add new mail domain with data submitted from web form (a dict).

    :param form: a dict of data submitted from web form.
    :param conn: ldap connection cursor
    """
    domain = form_utils.get_domain_name(form)

    # Check domain name.
    if not iredutils.is_domain(domain):
        return (False, 'INVALID_DOMAIN_NAME')

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    # Check whether domain name already exist (domainName, domainAliasName).
    if ldap_lib_general.is_domain_exists(domain=domain, conn=conn):
        return (False, 'ALREADY_EXISTS')

    dn = ldaputils.rdn_value_to_domain_dn(domain)

    # per-domain account settings
    _as = {}

    # Get name, transport
    cn = form_utils.get_single_value(form, input_name='cn', default_value=None)

    # Get default quota for newly created mail users.
    default_user_quota = form_utils.get_quota(form, input_name='defaultQuota')
    if default_user_quota:
        _as['defaultQuota'] = default_user_quota

    ldif = iredldif.ldif_domain(domain=domain,
                                cn=cn,
                                account_settings=_as)

    # msg: {key: value}
    msg = {}

    # Add domain dn.
    try:
        conn.add_s(dn, ldif)
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
    except ldap.LDAPError as e:
        msg[domain] = str(e)

    # Add default groups under domain.
    if attrs.DEFAULT_GROUPS:
        for i in attrs.DEFAULT_GROUPS:
            try:
                group_dn = 'ou=' + str(i) + ',' + str(dn)
                group_ldif = iredldif.ldif_group(str(i))

                conn.add_s(group_dn, group_ldif)
            except ldap.ALREADY_EXISTS:
                pass
            except Exception as e:
                msg[i] = repr(e)

    if not msg:
        return (True, )
    else:
        return (False, repr(msg))


def update(domain, profile_type, form, conn=None):
    """Update domain profile with data submitted from a web form.

    @domain -- the domain we're going to update
    @profile_type -- parameters under given profile type we're going to update
    @form -- dict of web form data
    @conn -- ldap connection cursor
    """
    domain = str(domain).lower()

    old_account_status = 'active'
    mod_attrs = []

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    qr = get_profile(domain=domain, conn=conn)
    if qr[0] is True:
        _ldif = qr[1]['ldif']
        old_account_status = _ldif.get('accountStatus', ['active'])[0]
    del qr

    # Allow normal admin to update profiles.
    if profile_type == 'general':
        mod_attrs += ldaputils.form_mod_attr(form=form, input_name='cn', attr='cn')

        ##################
        # Disclaimer
        #
        disclaimer = form_utils.get_single_value(form, input_name='disclaimer', default_value=None)

        if disclaimer:
            mod_attrs += ldaputils.mod_replace('disclaimer', disclaimer)
        else:
            mod_attrs += ldaputils.mod_replace('disclaimer', None)

    # Allow global admin to update profiles.
    if profile_type == 'general':
        # check account status.
        account_status = 'disabled'
        if 'accountStatus' in form:
            account_status = 'active'

        mod_attrs += ldaputils.mod_replace('accountStatus', account_status)

        if account_status != old_account_status:
            # Update all mail accounts with `domainStatus=disabled`
            qr = update_domain_status_for_all_accounts(domain=domain, status=account_status, conn=conn)
            if not qr[0]:
                return qr

    if mod_attrs:
        try:
            dn = ldaputils.rdn_value_to_domain_dn(domain)

            conn.modify_s(dn, mod_attrs)
            log_activity(msg="Update domain profile: {} ({}).".format(domain, profile_type),
                         domain=domain,
                         event='update')
            return (True, )
        except Exception as e:
            return (False, repr(e))

    return (True, )


def delete_domains(domains, keep_mailbox_days=0, conn=None):
    """Delete given domains, optionally, keep all mailboxes for given days.

    @domains -- a list/tuple/set of mail domain names.
    @keep_mailbox_days -- keep mailboxes under deleted domains for given days.
                          0 means forever (actually, kept for 100 years).
    @conn -- ldap connection cursor
    """
    if not domains:
        return (False, 'INVALID_DOMAIN_NAME')

    domains = [str(v).lower() for v in domains if iredutils.is_domain(v)]
    if not domains:
        return (True, )

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

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

    msg = {}
    for domain in domains:
        dn = ldaputils.rdn_value_to_domain_dn(web.safestr(domain))

        # Log maildir path in SQL table.
        try:
            qr = conn.search_s(attrs.DN_BETWEEN_USER_AND_DOMAIN + dn,
                               ldap.SCOPE_ONELEVEL,
                               "(objectClass=mailUser)",
                               ['mail', 'homeDirectory'])
            v = []
            for (_dn, _ldif) in qr:
                _ldif = iredutils.bytes2str(_ldif)

                deleted_maildir = _ldif.get('homeDirectory', [''])[0]
                deleted_mail = _ldif.get('mail')[0]

                if keep_mailbox_days == 0:
                    sql_keep_days = None
                else:
                    # Convert keep days to string
                    _now_in_seconds = time.time()
                    _days_in_seconds = _now_in_seconds + (keep_mailbox_days * 24 * 60 * 60)
                    sql_keep_days = time.strftime('%Y-%m-%d', time.localtime(_days_in_seconds))

                v += [{'maildir': deleted_maildir,
                       'username': deleted_mail,
                       'domain': domain,
                       'admin': session.get('username'),
                       'delete_date': sql_keep_days}]

            if v:
                web.conn_iredadmin.multiple_insert('deleted_mailboxes', values=v)
        except:
            log_traceback()

        # Remove domain object and leaves.
        _qr = ldap_lib_general.delete_ldap_tree(dn=dn, conn=conn)
        if not _qr[0]:
            return _qr

        log_activity(msg="Delete domain: %s." % (domain),
                     domain=domain,
                     event='delete')

    # Delete real-time mailbox quota.
    try:
        web.conn_iredadmin.delete(
            settings.SQL_TBL_USED_QUOTA,
            vars={'domains': domains},
            where='domain IN $domains',
        )
    except:
        log_traceback()

    if msg == {}:
        return (True, )
    else:
        return (False, repr(msg))


def get_enabled_services(domain, profile=None, conn=None):
    domain = str(domain).lower()
    if not iredutils.is_domain(domain):
        return (False, 'INVALID_DOMAIN_NAME')

    if not profile:
        dn = ldaputils.rdn_value_to_domain_dn(domain)
        qr = ldap_lib_general.get_profile_by_dn(dn=dn,
                                                attributes=['enabledService'],
                                                conn=conn)

        if not qr[0]:
            return qr

        profile = qr[1]['ldif']

    return profile.get('enabledService', [])
