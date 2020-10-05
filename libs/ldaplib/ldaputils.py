# Author: Zhang Huangbin <zhb@iredmail.org>

from typing import Dict, List, Tuple
import datetime
import web
import ldap
from ldap.dn import escape_dn_chars

import settings
from libs import iredutils, form_utils
from libs.ldaplib import attrs

session = web.config.get('_session')


def rdn_value_to_dn(keyword, account_type='user'):
    """Convert keyword and account type to DN."""
    keyword = web.safestr(keyword).strip().replace(' ', '')
    keyword = escape_dn_chars(keyword)
    account_type = web.safestr(account_type)

    # No matter what account type is, try to get a domain name.
    domain = keyword.split('@', 1)[-1]

    # Validate account type.
    if account_type not in attrs.ACCOUNT_TYPES_ALL:
        return 'INVALID_ACCOUNT_TYPE'

    # Validate keyword.
    # Keyword is email address.
    if account_type in attrs.ACCOUNT_TYPES_EMAIL and \
       not iredutils.is_email(keyword):
        return 'INVALID_MAIL'

    # Keyword is domain name.
    if account_type in attrs.ACCOUNT_TYPES_DOMAIN and \
       not iredutils.is_domain(keyword):
        return 'INVALID_DOMAIN_NAME'

    # Convert keyword to DN.
    if account_type == 'user':
        dn = '{}={},{}{}={},{}'.format(attrs.RDN_USER,
                                       keyword,
                                       attrs.DN_BETWEEN_USER_AND_DOMAIN,
                                       attrs.RDN_DOMAIN,
                                       domain,
                                       settings.ldap_basedn)
    elif account_type == 'admin':
        dn = '{}={},{}'.format(attrs.RDN_ADMIN,
                               keyword,
                               settings.ldap_domainadmin_dn)
    elif account_type == 'domain':
        dn = '{}={},{}'.format(attrs.RDN_DOMAIN,
                               keyword,
                               settings.ldap_basedn)

    return dn


def rdn_value_to_domain_dn(value):
    return rdn_value_to_dn(value, account_type='domain')


def rdn_value_to_user_dn(value):
    return rdn_value_to_dn(value, account_type='user')


def rdn_value_to_admin_dn(value):
    return rdn_value_to_dn(value, account_type='admin')


def rdn_value_to_ou_users_dn(value):
    # value must be a valid domain name.
    _domain_dn = rdn_value_to_domain_dn(value)
    return 'ou={},{}'.format(attrs.GROUP_USERS, _domain_dn)


def rdn_value_to_ou_maillists_dn(value):
    # value must be a valid domain name.
    _domain_dn = rdn_value_to_domain_dn(value)
    return 'ou={},{}'.format(attrs.GROUP_GROUPS, _domain_dn)


def rdn_value_to_ou_aliases_dn(value):
    # value must be a valid domain name.
    _domain_dn = rdn_value_to_domain_dn(value)
    return 'ou={},{}'.format(attrs.GROUP_ALIASES, _domain_dn)


def attr_ldif(attr, value, default=None, mode=None) -> List:
    """Generate a list of LDIF data with given attribute name and value.
    Returns empty list if no valid value.

    Value is properly handled with str/bytes/list/tuple/set types, and
    converted to list of bytes at the end.

    To generate ldif list with ldap modification like `ldap.MOD_REPLACE`,
    please use function `mod_replace()` instead.
    """
    v = value or default
    _ldif = []

    if v:
        if isinstance(value, (list, tuple, set)):
            lst = []
            for i in v:
                # Avoid duplicate element.
                if i in lst:
                    continue

                if isinstance(i, bytes):
                    lst.append(i)
                else:
                    lst.append(iredutils.str2bytes(i))

            v = lst
        elif isinstance(value, (int, float)):
            v = [str(v).encode()]
        else:
            v = [iredutils.str2bytes(v)]

    if mode == 'replace':
        if v:
            _ldif = [(ldap.MOD_REPLACE, attr, v)]
        else:
            _ldif = [(ldap.MOD_REPLACE, attr, None)]
    elif mode == 'add':
        if v:
            _ldif = [(ldap.MOD_ADD, attr, v)]
    elif mode == 'delete':
        if v or v is None:
            # Remove specified attr/value pair(s) if v is valid, or remove
            # completely if v is None.
            _ldif = [(ldap.MOD_DELETE, attr, v)]
    else:
        if v:
            # Used for adding ldap object.
            _ldif = [(attr, v)]

    return _ldif


def attrs_ldif(kvs: Dict) -> List:
    lst = []
    for (k, v) in kvs.items():
        lst += attr_ldif(k, v)

    return lst


# Return list of `ldap.MOD_REPLACE` operation.
def mod_replace(attr, value, default=None) -> List[Tuple]:
    """Return list of (only one) `ldap.MOD_REPLACE` used to remove of update
    LDAP value.

    When final value is `None` or empty list/tuple/set, LDAP
    attribute `attr` will be removed.

    >>> mod_replace(attr='name', value=None)
    [(2, 'name', None)]
    >>> mod_replace(attr='name', value='')
    [(2, 'name', None)]
    >>> mod_replace(attr='name', value=[])
    [(2, 'name', None)]
    >>> mod_replace(attr='name', value='', default=None)
    [(2, 'name', None)]
    >>> mod_replace(attr='name', value='my name')
    [(2, 'name', [b'my name'])]
    >>> mod_replace(attr='aint', value=5)
    [(2, 'aint', ['5'])]
    >>> mod_replace(attr='alist', value=['elm1', 'elm2'])
    [(2, 'alist', [b'elm1', b'elm2'])]
    >>> mod_replace(attr='atuple', value=('elm1', 'elm2'))
    [(2, 'atuple', [b'elm1', b'elm2'])]
    >>> mod_replace(attr='aset', value={'elm1', 'elm2'})
    [(2, 'aset', [b'elm1', b'elm2'])]
    """
    return attr_ldif(attr=attr, value=value, default=default, mode='replace')


def form_mod_attr(form,
                  input_name,
                  attr=None,
                  default_value=None,
                  to_string=False,
                  is_integer=False,
                  is_lowercase=False,
                  is_email=False):
    """Return a list of ldap.MOD_REPLACE with only one element.

    @form -- a dict of data submitted via web form
    @input_name -- the web form input name
    @attr -- LDAP attribute name used to store the value

    >>> form = {'myname': 'my name'}
    >>> form_mod_attr(form=form, input_name='myname', attr='cn')
    [(2, 'cn', [b'my name'])]
    >>> form_mod_attr(form=form, input_name='name', attr='cn')
    []
    """
    if input_name in form:
        if not attr:
            attr = input_name

        qr = form_utils.get_form_dict(form=form,
                                      input_name=input_name,
                                      key_name=attr,
                                      default_value=default_value,
                                      to_string=to_string,
                                      is_integer=is_integer)

        if qr:
            (k, v) = list(qr.items())[0]
            if v:
                if is_lowercase:
                    v = v.lower()

                if is_email:
                    if not iredutils.is_email(v):
                        v = default_value

                if v:
                    if attr == 'accountStatus':
                        if v not in ['active', 'disabled']:
                            v = 'disabled'

                    return mod_replace(k, v)
                else:
                    return []
            else:
                return mod_replace(k, None)

    return []


def form_mod_attrs_from_api(form,
                            input_name,
                            attr=None,
                            to_string=False,
                            to_lowercase=False,
                            is_domain=False,
                            is_email=False):
    """Return a list of (one) ldap.MOD_REPLACE operation.
    `form` is a API request.
    """
    if input_name in form:
        if not attr:
            attr = input_name

        values = form_utils.get_multi_values_from_api(
            form=form,
            input_name=input_name,
            to_string=to_string,
            to_lowercase=to_lowercase,
            is_domain=is_domain,
            is_email=is_email,
        )

        values = [v.strip() for v in values if v]
        return mod_replace(attr, values)

    return []


def account_setting_list_to_dict(setting_list) -> Dict:
    """Return a dict of 'accountSetting' values."""
    setting_dict = {}

    for item in setting_list:
        item = iredutils.bytes2str(item)

        if ':' in item:
            (k, v) = item.split(':', 1)

            if k in ['defaultQuota', 'maxUserQuota',
                     'minPasswordLength', 'maxPasswordLength',
                     'numberOfUsers', 'numberOfAliases', 'numberOfLists',
                     # Per-admin domain creation settings
                     'create_max_domains', 'create_max_quota',
                     'create_max_users', 'create_max_aliases', 'create_max_lists']:
                # Value of these settings must be integer or '-1' (except 'maxUserQuota').
                # '-1' means not allowed to add this kind of account.
                if v.isdigit() or v == '-1':
                    setting_dict[k] = int(v)
            elif k in ['disabledDomainProfile',
                       'disabledUserProfile',
                       'disabledUserPreference',
                       'disabledMailService']:
                # These settings contains multiple values
                # ldap value format: key:v1,v2,v3
                v = v.lower()

                if k in setting_dict:
                    setting_dict[k].append(v)
                else:
                    setting_dict[k] = [v]
            elif k in ['defaultList']:
                setting_dict[k] = v.split(',')
            else:
                setting_dict[k] = v

    return setting_dict


def account_setting_dict_to_list(setting_dict: Dict) -> List[bytes]:
    setting_list = []

    for (k, v) in list(setting_dict.items()):
        if not v:
            continue

        if isinstance(v, (list, tuple, set)):
            # ldap value format: key:v1,v2,v3
            if k in ['disabledDomainProfile',
                     'disabledUserProfile',
                     'disabledUserPreference',
                     'disabledMailService']:
                for j in v:
                    item = "{}:{}".format(k, j).encode()
                    setting_list.append(item)
            else:
                st = "{}:{}".format(k, ','.join(v)).encode()
                setting_list.append(st)
        else:
            # single string
            st = "{}:{}".format(k, v).encode()
            setting_list.append(st)

    return list(set(setting_list))


def get_account_setting_from_profile(ldif) -> Dict:
    """Get account settings from LDIF data (a dict) of account object."""
    _qr = ldif.get('accountSetting', [])

    if _qr:
        _as = account_setting_list_to_dict(_qr)
    else:
        _as = {}

    return _as


# Get accountSetting from ldap query result
def get_account_settings_from_qr(ldap_query_result, key='domainName') -> Dict:
    """Return value (in dict) of 'accountSetting' attribute from LDAP query.

    >> all_account_settings = {
    ..     'key1': {
    ..             'var1': 'value',
    ..             'var2': ['value1', 'value2'],
    ..             ...
    ..             },
    ..     'key2': {
    ..             'var1': 'value',
    ..             ...
    ..             },
    ..     ...
    .. }
    """
    if not isinstance(ldap_query_result, list):
        return {}

    all_account_settings = {}
    if ldap_query_result:
        for (_dn, _ldif) in ldap_query_result:
            _ldif = iredutils.bytes2str(_ldif)
            value_of_key = _ldif[key][0]
            account_setting = _ldif.get('accountSetting', [])
            if account_setting:
                all_account_settings[value_of_key] = account_setting_list_to_dict(account_setting)
            else:
                all_account_settings[value_of_key] = {}

    return all_account_settings


def get_days_of_shadow_last_change(year=None, month=None, day=None) -> int:
    """Return number of days since 1970-01-01."""
    today = datetime.date.today()

    if not year:
        year = today.year

    if not month:
        month = today.month

    if not day:
        day = today.day

    try:
        return (datetime.date(year, month, day) - datetime.date(1970, 1, 1)).days
    except:
        return 0


# LDIF: [('attr1': [value1, value2]),
#        ('attr2': [value1, vlaue2]),
#        ...]
#
# Dict: {'attr1': [value1, value2],
#        'attr2': [value1, value2],
#        ...}
def ldif_to_dict(ldif) -> Dict:
    ldif_dict = {}

    for item in ldif:
        ldif_dict[item[0]] = item[1]

    return ldif_dict


def dict_to_ldif(ldif_dict) -> List[Tuple]:
    ldif = []

    for (key, value) in list(ldif_dict.items()):
        ldif.append((key, value))

    return ldif


def get_custom_user_attributes(domain=None):
    """Get allowed custom attributes for specified domain."""
    # Additional managed LDAP attributes
    _managed_attrs = settings.ADDITIONAL_MANAGED_USER_ATTRIBUTES

    # Re-construct managed ldap attributes
    custom_attrs = {}

    # Remove disallowed attrs first.
    for attr in _managed_attrs:
        _attr_entries = _managed_attrs[attr]

        _attr_allowed_domains = _attr_entries.get('allowed_domains', [])
        if _attr_entries.get('allowed_domains'):
            if domain not in _attr_allowed_domains:
                continue

        _attr_properties = _attr_entries.get('properties', [])
        if 'require_global_admin' in _attr_properties:
            if not session.get('is_global_admin'):
                continue

        custom_attrs[attr] = _attr_entries

    # Make sure attribute has required preferences: desc, properties. Used in
    # Jinja2 template files.
    for attr in custom_attrs:
        _attr_entries = custom_attrs[attr]

        if 'desc' not in _attr_entries:
            # Set 'desc' to attribute name.
            custom_attrs[attr]['desc'] = attr

        _attr_properties = _attr_entries.get('properties', [])
        # Make sure we have a valid properties
        if not _attr_properties:
            # Set default properties
            custom_attrs[attr]['properties'] = ['string']

        # if no data type, reset it to string.
        if ('string' not in _attr_entries['properties']) and \
           ('text' not in _attr_entries['properties']) and \
           ('integer' not in _attr_entries['properties']):
            custom_attrs[attr]['properties'] += ['string']

    return custom_attrs
