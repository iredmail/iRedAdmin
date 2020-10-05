# Author: Zhang Huangbin <zhb@iredmail.org>

import ldap
import web
import settings
from libs import iredutils, iredpwd, form_utils
from libs.l10n import TIMEZONES
from libs.logger import log_activity

from libs.ldaplib.core import LDAPWrap
from libs.ldaplib import attrs, ldaputils, iredldif
from libs.ldaplib import general as ldap_lib_general

session = web.config.get('_session')


def get_profile(mail, attributes=None, conn=None):
    """Get admin profile."""
    mail = web.safestr(mail)
    dn = ldaputils.rdn_value_to_admin_dn(mail)

    if not attributes:
        attributes = list(attrs.ADMIN_ATTRS_ALL)

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    try:
        qr = conn.search_s(dn,
                           ldap.SCOPE_BASE,
                           '(&(objectClass=mailAdmin)(mail=%s))' % mail,
                           attributes)

        (_dn, _ldif) = qr[0]
        return (True, {'dn': _dn, 'ldif': iredutils.bytes2str(_ldif)})
    except ldap.NO_SUCH_OBJECT:
        return (False, 'NO_SUCH_ACCOUNT')
    except Exception as e:
        return (False, repr(e))


def get_managed_domains(admin,
                        attributes=None,
                        domain_name_only=True,
                        conn=None):
    """Get domains managed by given admin.

    :param admin: email address of domain admin
    :param attributes: LDAP attribute names used when `domain_name_only=False`.
    :param domain_name_only: If `True`, return a list of domain names.
                             Otherwise return full LDIF data (dict).
    :param conn: ldap connection cursor
    """
    admin = str(admin).lower()
    if not iredutils.is_email(admin):
        return (False, 'INVALID_ADMIN')

    if admin == session.get('username') and session.get('is_global_admin'):
        _filter = '(objectClass=mailDomain)'
    else:
        _filter = '(&(objectClass=mailDomain)(domainAdmin=%s))' % admin

    if not attributes:
        attributes = list(attrs.ADMIN_ATTRS_ALL)

    # We need attr 'domainName'
    if 'domainName' not in attributes:
        attributes.append('domainName')

    try:
        if not conn:
            _wrap = LDAPWrap()
            conn = _wrap.conn

        qr = conn.search_s(settings.ldap_basedn,
                           ldap.SCOPE_ONELEVEL,
                           _filter,
                           attributes)

        if domain_name_only:
            # Return list of domain names.
            domains = []
            for (_dn, _ldif) in qr:
                _ldif = iredutils.bytes2str(_ldif)
                domains += _ldif.get('domainName', [])

            domains = [d.lower() for d in domains]
            domains.sort()

            return (True, domains)
        else:
            qr = iredutils.bytes2str(qr)
            qr.sort()
            return (True, qr)
    except Exception as e:
        return (False, repr(e))


def get_standalone_admin_emails(conn=None):
    """Return a list of standalone admins' email addresses."""
    emails = []
    try:
        if not conn:
            _wrap = LDAPWrap()
            conn = _wrap.conn

        qr = conn.search_s(settings.ldap_domainadmin_dn,
                           ldap.SCOPE_ONELEVEL,
                           '(objectClass=mailAdmin)',
                           ['mail'])

        for (_dn, _ldif) in qr:
            _ldif = iredutils.bytes2str(_ldif)
            emails += _ldif['mail']

        # Sort and remove duplicate emails.
        emails = list(set(emails))

        return (True, emails)
    except Exception as e:
        return (False, repr(e))


def list_accounts(attributes=None, email_only=False, conn=None):
    """List all admin accounts."""
    if not attributes:
        attributes = list(attrs.ADMIN_SEARCH_ATTRS)

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    try:
        # Get standalone admins
        qr_admins = conn.search_s(settings.ldap_domainadmin_dn,
                                  ldap.SCOPE_ONELEVEL,
                                  '(objectClass=mailAdmin)',
                                  attributes)

        # Get mail users with admin privileges
        _filter = '(&(objectClass=mailUser)(accountStatus=active)(domainGlobalAdmin=yes))'
        qr_users = conn.search_s(settings.ldap_basedn,
                                 ldap.SCOPE_SUBTREE,
                                 _filter,
                                 attributes)

        if email_only:
            emails = []
            for (_dn, _ldif) in qr_admins:
                _ldif = iredutils.bytes2str(_ldif)
                emails += _ldif.get('mail', [])

            for (_dn, _ldif) in qr_users:
                _ldif = iredutils.bytes2str(_ldif)
                emails += _ldif.get('mail', [])

            # Remove duplicate mail addresses.
            emails = list(set(emails))

            return (True, emails)
        else:
            return (True, iredutils.bytes2str(qr_admins) + iredutils.bytes2str(qr_users))
    except Exception as e:
        return (False, repr(e))


def num_managed_domains(admin=None, conn=None):
    if not admin:
        admin = session.get('username')
    else:
        admin = str(admin).lower()
        if not iredutils.is_email(admin):
            return 0

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    qr = get_managed_domains(admin=admin,
                             conn=conn,
                             attributes=['domainName'])
    if qr[0]:
        domains = qr[1]
        return len(domains)
    else:
        return 0


def add(form, conn=None):
    """Add new standalone admin account."""
    mail = form_utils.get_single_value(form=form,
                                       input_name='mail',
                                       to_lowercase=True,
                                       to_string=True)

    if not iredutils.is_auth_email(mail):
        return (False, 'INVALID_MAIL')

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    # Make sure it's not hosted domain
    domain = mail.split('@', 1)[-1]
    if ldap_lib_general.is_domain_exists(domain=domain, conn=conn):
        return (False, 'CAN_NOT_BE_LOCAL_DOMAIN')

    name = form_utils.get_single_value(form=form, input_name='cn')
    account_status = form_utils.get_single_value(form=form,
                                                 input_name='accountStatus',
                                                 default_value='active',
                                                 to_string=True)
    lang = form_utils.get_single_value(form=form,
                                       input_name='preferredLanguage',
                                       to_string=True)

    # Check password.
    newpw = web.safestr(form.get('newpw'))
    confirmpw = web.safestr(form.get('confirmpw'))

    result = iredpwd.verify_new_password(newpw, confirmpw)
    if result[0] is True:
        passwd = iredpwd.generate_password_hash(result[1])
    else:
        return result

    ldif = iredldif.ldif_mailadmin(mail=mail,
                                   passwd=passwd,
                                   cn=name,
                                   account_status=account_status,
                                   preferred_language=lang)

    dn = ldaputils.rdn_value_to_admin_dn(mail)

    try:
        conn.add_s(dn, ldif)
        log_activity(msg="Create admin: %s." % (mail), event='create')
        return (True, )
    except ldap.ALREADY_EXISTS:
        return (False, 'ALREADY_EXISTS')
    except Exception as e:
        return (False, repr(e))


def delete(mails, revoke_admin_privilege_from_user=True, conn=None):
    """
    Delete standalone domain admin accounts, or revoke admin privilege from
    mail user which is domain admin.

    :param mails: list of domain admin email addresses
    :param revoke_admin_privilege_from_user: if @mails contains mail user which
              has domain admin privilege, we should revoke the privilege.
    :param conn: ldap connection cursor
    """
    mails = [str(i).lower() for i in mails if iredutils.is_email(i)]
    if not mails:
        return (True, )

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    result = {}

    for mail in mails:
        # Get dn of admin account under o=domainAdmins
        dn = ldaputils.rdn_value_to_admin_dn(mail)

        try:
            conn.delete_s(dn)
            log_activity(msg="Delete admin: %s." % (mail), event='delete')
        except ldap.NO_SUCH_OBJECT:
            if revoke_admin_privilege_from_user:
                # This is a mail user admin
                dn = ldaputils.rdn_value_to_user_dn(mail)
                try:
                    # Delete enabledService=domainadmin
                    ldap_lib_general.remove_attr_values(dn=dn,
                                                        attr='enabledService',
                                                        values=['domainadmin'],
                                                        conn=conn)

                    # Delete domainGlobalAdmin=yes
                    ldap_lib_general.remove_attr_values(dn=dn,
                                                        attr='domainGlobalAdmin',
                                                        values=['yes'],
                                                        conn=conn)

                    log_activity(msg="Revoke domain admin privilege: %s." % (mail), event='delete')
                except Exception as e:
                    result[mail] = str(e)
        except ldap.LDAPError as e:
            result[mail] = str(e)

    if result == {}:
        return (True, )
    else:
        return (False, repr(result))


# Update admin profile.
def update_profile(form, mail, profile_type, conn=None):
    mail = web.safestr(mail).lower()
    username = mail.split('@', 1)[0]

    if (not session.get('is_global_admin')) and (session.get('username') != mail):
        # Don't allow to view/update other admins' profile.
        return (False, 'PERMISSION_DENIED')

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    dn = ldaputils.rdn_value_to_admin_dn(mail)

    mod_attrs = []
    if profile_type == 'general':
        # Get preferredLanguage.
        lang = form_utils.get_language(form)
        mod_attrs += ldaputils.mod_replace('preferredLanguage', lang)

        # Get cn.
        cn = form.get('cn', None)
        mod_attrs += ldaputils.mod_replace(attr='cn',
                                           value=cn,
                                           default=username)

        first_name = form.get('first_name', '')
        mod_attrs += ldaputils.mod_replace(attr='givenName',
                                           value=first_name,
                                           default=username)

        last_name = form.get('last_name', '')
        mod_attrs += ldaputils.mod_replace(attr='sn',
                                           value=last_name,
                                           default=username)

        # Get account setting
        _qr = ldap_lib_general.get_admin_account_setting(mail=mail,
                                                         profile=None,
                                                         conn=conn)
        if not _qr[0]:
            return _qr

        _as = _qr[1]

        # Update timezone
        tz_name = form_utils.get_timezone(form)

        if tz_name:
            _as['timezone'] = tz_name

            if session['username'] == mail:
                session['timezone'] = TIMEZONES[tz_name]

        if session.get('is_global_admin'):
            # check account status.
            account_status = 'disabled'
            if 'accountStatus' in form:
                account_status = 'active'

            mod_attrs += ldaputils.mod_replace('accountStatus', account_status)

            # Get domainGlobalAdmin.
            if 'domainGlobalAdmin' in form:
                mod_attrs += ldaputils.mod_replace('domainGlobalAdmin', 'yes')
            else:
                mod_attrs += ldaputils.mod_replace('domainGlobalAdmin', None)

        try:
            # Modify profiles.
            conn.modify_s(dn, mod_attrs)

            if session.get('username') == mail and session.get('lang') != lang:
                session['lang'] = lang
        except Exception as e:
            return (False, repr(e))

    elif profile_type == 'password':
        cur_passwd = web.safestr(form.get('oldpw', ''))
        newpw = web.safestr(form.get('newpw', ''))
        confirmpw = web.safestr(form.get('confirmpw', ''))

        _qr = iredpwd.verify_new_password(newpw, confirmpw)
        if _qr[0]:
            passwd = _qr[1]
        else:
            return _qr

        # Change password.
        if session.get('is_global_admin'):
            # Reset password without verify old password.
            cur_passwd = None

        _qr = ldap_lib_general.change_password(dn=dn,
                                               old_password=cur_passwd,
                                               new_password=passwd,
                                               conn=conn)

        if _qr[0]:
            return (True, )
        else:
            return _qr
