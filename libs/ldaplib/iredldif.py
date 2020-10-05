# Author: Zhang Huangbin <zhb@iredmail.org>
#
# NOTES:
#
#   o always use `ldaputils.attr_ldif()` or `ldaputils.attrs_ldif()` to
#     construct ldif list(s) used for LDAP object CREATION.
#                                                 ^^^^^^^^
#   o always use `ldaputils.mod_replace()` to construct ldif list used for LDAP
#     object MODIFICATION.
#            ^^^^^^^^^^^^

import os
import web
import settings
from libs import iredutils
from libs.ldaplib import ldaputils, attrs


def ldif_domain(domain,
                cn=None,
                transport=None,
                account_status=None,
                account_settings=None):
    """Return LDIF structure of mail domain used for creation."""
    domain = domain.lower()

    if not transport:
        transport = settings.default_mta_transport

    _enabled_services = list(set(list(attrs.DOMAIN_ENABLED_SERVICE_FOR_NEW_DOMAIN) + settings.ADDITIONAL_ENABLED_DOMAIN_SERVICES))
    _enabled_services = [i
                         for i in _enabled_services
                         if i not in settings.ADDITIONAL_DISABLED_DOMAIN_SERVICES]

    ldif = ldaputils.attrs_ldif({
        'objectClass': 'mailDomain',
        'domainName': domain,
        'mtaTransport': transport,
        'enabledService': _enabled_services,
        'cn': cn,
    })

    if account_status in ['active', None]:
        ldif += ldaputils.attr_ldif('accountStatus', 'active')
    else:
        ldif += ldaputils.attr_ldif('accountStatus', 'disabled')

    if account_settings:
        _as = ldaputils.account_setting_dict_to_list(account_settings)
        ldif += ldaputils.attr_ldif('accountSetting', _as)

    return ldif


def ldif_group(name):
    ldif = ldaputils.attrs_ldif({
        'objectClass': 'organizationalUnit',
        'ou': name,
    })
    return ldif


# Define and return LDIF structure of domain admin.
def ldif_mailadmin(mail,
                   passwd,
                   cn,
                   account_status=None,
                   preferred_language=None,
                   account_setting=None,
                   disabled_services=None):
    """Generate LDIF used to create a standalone domain admin account.

    :param mail: full email address. The mail domain cannot be one of locally
                 hosted domain.
    :param passwd: hashed password string
    :param cn: the display name of this admin
    :param account_status: account status (active, disabled)
    :param preferred_language: short code of preferred language. e.g. en_US.
    :param is_global_admin: mark this admin as a global admin (yes, no)
    :param account_setting: a dict of per-account settings.
    :param disabled_services: a list/tupe/set of disabled services.
    """
    mail = web.safestr(mail).lower()

    if account_status not in ['active', 'disabled']:
        account_status = 'disabled'

    ldif = ldaputils.attrs_ldif({
        'objectClass': 'mailAdmin',
        'mail': mail,
        'userPassword': passwd,
        'accountStatus': account_status,
        'domainGlobalAdmin': 'yes',
        'shadowLastChange': ldaputils.get_days_of_shadow_last_change(),
        'cn': cn,
        'disabledService': disabled_services,
    })

    if preferred_language:
        if preferred_language in iredutils.get_language_maps():
            ldif += ldaputils.attr_ldif("preferredLanguage", preferred_language)

    if account_setting and isinstance(account_setting, dict):
        _as = ldaputils.account_setting_dict_to_list(account_setting)
        ldif += ldaputils.attr_ldif("accountSetting", _as)

    return ldif


# Define and return LDIF structure of mail user.
def ldif_mailuser(domain,
                  username,
                  cn,
                  passwd,
                  quota=0,
                  storage_base_directory=None,
                  mailbox_format=None,
                  mailbox_folder=None,
                  mailbox_maildir=None,
                  language=None,
                  disabled_services=None,
                  domain_status=None):
    domain = str(domain).lower()
    username = str(username).strip().replace(' ', '').lower()
    mail = username + '@' + domain
    if not cn:
        cn = username

    if not (storage_base_directory and os.path.isabs(storage_base_directory)):
        storage_base_directory = settings.storage_base_directory

    if mailbox_maildir and os.path.isabs(mailbox_maildir):
        home_directory = str(mailbox_maildir).lower()
    else:
        home_directory = os.path.join(storage_base_directory, iredutils.generate_maildir_path(mail))

    enabled_services = list(attrs.USER_SERVICES_OF_NORMAL_USER) + settings.ADDITIONAL_ENABLED_USER_SERVICES

    if disabled_services:
        enabled_services = set(enabled_services) - set(disabled_services)
        enabled_services = list(enabled_services)

    lang = language or settings.default_language
    if lang not in iredutils.get_language_maps():
        lang = None

    # Generate basic LDIF.
    ldif = ldaputils.attrs_ldif({
        'objectClass': ['inetOrgPerson', 'mailUser', 'shadowAccount', 'amavisAccount'],
        'mail': mail,
        'userPassword': passwd,
        'cn': cn,
        'sn': username,
        'uid': username,
        'homeDirectory': home_directory,
        'accountStatus': 'active',
        'enabledService': enabled_services,
        'preferredLanguage': lang,
        # shadowAccount integration.
        'shadowLastChange': ldaputils.get_days_of_shadow_last_change(),
        # Amavisd integration.
        'amavisLocal': 'TRUE',
    })

    # Append quota. No 'mailQuota' attribute means unlimited.
    quota = str(quota).strip()
    if quota.isdigit():
        quota = int(int(quota) * 1024 * 1024)
        ldif += ldaputils.attr_ldif('mailQuota', quota)

    # Append mailbox format.
    if mailbox_format:
        ldif += ldaputils.attr_ldif('mailboxFormat', str(mailbox_format).lower())

    # mailbox folder
    if mailbox_folder:
        ldif += ldaputils.attr_ldif('mailboxFolder', mailbox_folder)

    if domain_status not in ['active', None]:
        ldif += ldaputils.attr_ldif('domainStatus', 'disabled')

    return ldif
