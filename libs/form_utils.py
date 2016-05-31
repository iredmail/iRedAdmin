"""Functions used to extract required data from web form."""

import settings
from libs import iredutils
from libs.languages import get_language_maps


# Return single value of specified form name.
def get_single_value(form,
                     input_name,
                     default_value='',
                     is_domain=False,
                     is_email=False,
                     is_integer=False,
                     to_lowercase=False,
                     to_uppercase=False,
                     to_string=False):
    v = form.get(input_name, '')
    if not v:
        v = default_value

    if is_domain:
        if not iredutils.is_domain(v):
            return ''

    if is_email:
        if not iredutils.is_email(v):
            v = default_value

    if is_integer:
        try:
            v = int(v)
        except:
            v = default_value

    if to_lowercase:
        v = str(v).lower()

    if to_uppercase:
        v = v.upper()

    if to_string:
        v = str(v)

    return v


# Return single value of specified form name.
def get_multi_values(form,
                     input_name,
                     default_value=None,
                     input_is_textarea=False,
                     is_domain=False,
                     is_email=False,
                     to_lowercase=False,
                     to_uppercase=False):
    v = form.get(input_name)
    if v:
        if input_is_textarea:
            v = v.splitlines()
    else:
        v = default_value

    # Remove duplicate items.
    v = list(set(v))

    if is_domain:
        v = [str(i).lower() for i in v if iredutils.is_domain(i)]

    if is_email:
        v = [str(i).lower() for i in v if iredutils.is_email(i)]

    if to_lowercase:
        if not (is_domain or is_email):
            v = [i.lower() for i in v]

    if to_uppercase:
        if not (is_domain or is_email):
            v = [i.upper() for i in v]

    return v


def get_domain_name(form, input_name='domainName'):
    return get_single_value(form,
                            input_name=input_name,
                            default_value=None,
                            is_domain=True,
                            to_lowercase=True,
                            to_string=True)


def get_domain_names(form, input_name='domainName'):
    return get_multi_values(form,
                            input_name=input_name,
                            default_value=None,
                            is_domain=True,
                            to_lowercase=True)


# Get default language for new mail user from web form.
def get_language(form, input_name='preferredLanguage'):
    lang = get_single_value(form, input_name=input_name, to_string=True)
    if lang not in get_language_maps():
        lang = ''

    return lang


# Get domain quota (in MB). 0 means unlimited.
def get_domain_quota_and_unit(form,
                              input_quota='domainQuota',
                              input_quota_unit='domainQuotaUnit'):
    # multiply is used for SQL backends.
    domain_quota = str(form.get('domainQuota'))
    if domain_quota.isdigit():
        domain_quota = int(domain_quota)
    else:
        domain_quota = 0

    domain_quota_unit = 'MB'
    if domain_quota > 0:
        domain_quota_unit = str(form.get('domainQuotaUnit'))
        if settings.backend in ['mysql', 'pgsql']:
            if domain_quota_unit == 'GB':
                domain_quota = domain_quota * 1024
            elif domain_quota_unit == 'TB':
                domain_quota = domain_quota * 1024 * 1024

    return {'quota': domain_quota, 'unit': domain_quota_unit}


# Get mailbox quota (in MB).
def get_quota(form, input_name='defaultQuota', default=0):
    quota = str(form.get(input_name))
    if quota.isdigit():
        quota = abs(int(quota))

        if input_name == 'maxUserQuota':
            quota_unit = str(form.get('maxUserQuotaUnit', 'MB'))
            if quota_unit == 'TB':
                quota = quota * 1024 * 1024
            elif quota_unit == 'GB':
                quota = quota * 1024
            else:
                # MB
                pass
    else:
        quota = default

    return quota


# iRedAPD: Get throttle setting for
def get_throttle_setting(form, account, inout_type='inbound'):
    # inout_type -- inbound, outbound.
    var_enable_throttle = 'enable_%s_throttling' % inout_type

    # not enabled.
    if var_enable_throttle not in form:
        return {}

    # name of form <input> tag:
    # [inout_type]_[name]
    # custom_[inout_type]_[name]

    # Pre-defined values
    setting = {'period': 0,
               'max_msgs': 0,
               'max_quota': 0,
               'msg_size': 0,
               'kind': inout_type}

    for k in ['period', 'max_msgs', 'max_quota', 'msg_size']:
        var = inout_type + '_' + k

        # Get pre-defined value first
        v = form.get(var, '')

        if not v.isdigit():
            # Get custom value if it's not pre-defined
            v = form.get('custom_' + var, '0')

        # Value '-1' means inherit settings from lower priority throttle setting.
        if v.lstrip('-').isdigit():
            setting[k] = int(v)
        else:
            setting[k] = 0

    setting['account'] = account
    setting['priority'] = iredutils.get_account_priority(account)

    # Return empty dict if all values are 0.
    return setting


def get_account_status(form,
                       input_name='accountStatus',
                       default_value='active',
                       to_integer=False):
    status = get_single_value(form, input_name=input_name, to_string=True)

    if not (status in ['active', 'disabled']):
        status = default_value

    # SQL backends store the account status as `active=[1|0]`
    # LDAP backends store the account status as `accountStatus=[active|disabled]`
    if to_integer:
        if status == 'active':
            return 1
        else:
            return 0
    else:
        return status
