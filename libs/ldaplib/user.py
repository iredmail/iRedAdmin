# Author: Zhang Huangbin <zhb@iredmail.org>

import os
import time
import ldap
import web
import settings

from libs import iredutils, iredpwd, form_utils
from libs.l10n import TIMEZONES
from libs.logger import log_activity

from libs.ldaplib.core import LDAPWrap
from libs.ldaplib import attrs, ldaputils, iredldif
from libs.ldaplib import domain as ldap_lib_domain
from libs.ldaplib import general as ldap_lib_general
from libs.ldaplib import decorators

session = web.config.get('_session')


# List all users under one domain.
@decorators.require_global_admin
def list_accounts(domain,
                  search_filter=None,
                  attrlist=None,
                  email_only=False,
                  disabled_only=False,
                  conn=None):
    # Update number of existing users in domain profile.
    update_count = False

    if not search_filter:
        # Use '(!(mail=@domain.com))' to hide catch-all account.
        search_filter = '(&(objectClass=mailUser)(!(mail=@%s)))' % domain
        update_count = True

    if disabled_only:
        # use "is True" here to prevent client input invalid value in url.
        search_filter = '(&' + search_filter + '(accountStatus=disabled)' + ')'

    if not attrlist:
        if email_only:
            attrlist = ['mail']
        else:
            attrlist = list(attrs.USER_SEARCH_ATTRS)

    dn_domain = ldaputils.rdn_value_to_domain_dn(domain)

    # Search only admins INSIDE same domain.
    dn = attrs.DN_BETWEEN_USER_AND_DOMAIN + dn_domain

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    try:
        qr = conn.search_s(dn,
                           ldap.SCOPE_ONELEVEL,
                           search_filter,
                           attrlist)
        if qr:
            qr = iredutils.bytes2str(qr)

        _emails = []
        if email_only:
            for (_dn, _ldif) in qr:
                _emails += _ldif.get('mail', [])

            _emails.sort()

        if update_count:
            # Reset number of existing users in domain profile.
            ldap_lib_general.reset_num_domain_current_users(domain=domain,
                                                            num=len(qr),
                                                            conn=conn)

        if email_only:
            return (True, _emails)
        else:
            return (True, qr)
    except ldap.NO_SUCH_OBJECT:
        return (False, 'NO_SUCH_ACCOUNT')
    except ldap.SIZELIMIT_EXCEEDED:
        return (False, 'EXCEEDED_LDAP_SERVER_SIZELIMIT')
    except Exception as e:
        return (False, repr(e))


@decorators.require_global_admin
def get_profile(mail, attributes=None, conn=None):
    """Get user profile.

    :param mail: full email address or '@domain.com' (catch-all account)
    :param attributes: list of LDAP attribute names
    :param conn: LDAP connection cursor

    Returned data:

    - (True, {'dn': '<full_dn>', 'ldif': dict})
    - (False, <error_reason>)
    """
    if not attributes:
        attributes = list(attrs.USER_ATTRS_ALL)

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    try:
        dn = ldaputils.rdn_value_to_user_dn(mail)
        _filter = '(&(objectClass=mailUser)(mail=%s))' % (mail)

        qr = ldap_lib_general.get_profile_by_dn(dn=dn,
                                                query_filter=_filter,
                                                attributes=attributes,
                                                conn=conn)

        if not qr[0]:
            return qr

        _dn = qr[1]['dn']
        _ldif = qr[1]['ldif']

        # Normal domain admin is not allowed to view/update global admin profile
        if not session.get('is_global_admin'):
            if _ldif.get('domainGlobalAdmin', ['no']) == ['yes']:
                return (False, 'PERMISSION_DENIED_UPDATE_GLOBAL_ADMIN_PROFILE')

        # Sort some lists
        for k in ['shadowAddress', 'mailForwardingAddress']:
            if k in _ldif:
                _addrs = _ldif[k]
                _addrs.sort()
                _ldif[k] = _addrs

        return (True, {'dn': _dn, 'ldif': _ldif})
    except ldap.NO_SUCH_OBJECT:
        return (False, 'NO_SUCH_ACCOUNT')
    except Exception as e:
        return (False, repr(e))


@decorators.require_global_admin
def get_user_forwardings(mail, profile=None, conn=None):
    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    if not profile:
        _qr = get_profile(mail=mail, attributes=['mailForwardingAddress'], conn=conn)
        if not _qr[0]:
            return _qr

        profile = _qr[1]['ldif']

    _addresses = [i.lower() for i in profile.get('mailForwardingAddress', [])]
    _addresses = list(set(_addresses))

    return (True, _addresses)


def user_is_global_admin(mail, user_profile=None, conn=None):
    if not user_profile:
        if not conn:
            _wrap = LDAPWrap()
            conn = _wrap.conn

        dn = ldaputils.rdn_value_to_user_dn(mail)
        search_filter = '(&(objectClass=mailUser)(mail=%s))' % (mail)
        search_scope = ldap.SCOPE_BASE
        try:
            qr = conn.search_s(dn,
                               search_scope,
                               search_filter,
                               ['domainGlobalAdmin'])

            if qr:
                user_profile = iredutils.bytes2str(qr[0][1])
        except ldap.NO_SUCH_OBJECT:
            return False
        except:
            return False

    if user_profile.get('domainGlobalAdmin', ['no'])[0] == 'yes':
        return True
    else:
        return False


def reset_forwardings(mail, forwardings=None, conn=None):
    if forwardings:
        _addresses = [str(v).lower()
                      for v in forwardings
                      if iredutils.is_email(v)]
    else:
        _addresses = []

    # Remove duplicate addresses
    if _addresses:
        _addresses = list(set(_addresses))

    # Remove non-existing addresses in same domain.
    domain = mail.split('@', 1)[-1]
    addrs_in_domain = set()
    addrs_not_in_domain = set()

    for addr in _addresses:
        if addr.endswith('@' + domain):
            addrs_in_domain.add(addr)
        else:
            addrs_not_in_domain.add(addr)

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    # Get existing addresses
    valid_addrs_in_domain = set()
    if addrs_in_domain:
        dn = ldaputils.rdn_value_to_domain_dn(domain)
        _qr = ldap_lib_general.filter_existing_emails(mails=addrs_in_domain,
                                                      base_dn=dn,
                                                      conn=conn)

        valid_addrs_in_domain = set(_qr['exist'])

    fwd_addrs = list(valid_addrs_in_domain | addrs_not_in_domain)

    if fwd_addrs:
        mod_attr = ldaputils.mod_replace('mailForwardingAddress', fwd_addrs)
    else:
        mod_attr = ldaputils.mod_replace('mailForwardingAddress', None)

    try:
        dn = ldaputils.rdn_value_to_user_dn(mail)
        conn.modify_s(dn, mod_attr)
        return (True, )
    except Exception as e:
        return (False, repr(e))


@decorators.require_global_admin
def update_managed_user_attrs(domain, mail, mod_attrs, conn=None):
    """Update custom LDAP attributes of mail user account.

    @domain - the domain which contains specified user (@mail)
    @mail - full email address of mail user
    @mod_attrs - a list of ldap.MOD_REPLACE actions
    @conn - LDAP connection cursor
    """
    if not mail.endswith('@' + domain):
        raise web.seeother('/domains?msg=PERMISSION_DENIED')

    if not mod_attrs:
        return (True, )

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    try:
        dn = ldaputils.rdn_value_to_user_dn(mail)
        conn.modify_s(dn, mod_attrs)
        return (True, )
    except Exception as e:
        return (False, repr(e))


@decorators.require_global_admin
def add(domain, form, conn=None):
    # Get domain name, username, cn.
    form_domain = form_utils.get_domain_name(form)
    if not (domain == form_domain):
        return (False, 'INVALID_DOMAIN_NAME')

    username = web.safestr(form.get('username')).strip().lower()
    mail = username + '@' + domain
    mail = iredutils.strip_mail_ext_address(mail)

    if not iredutils.is_auth_email(mail):
        return (False, 'INVALID_MAIL')

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    _qr = ldap_lib_general.check_account_existence(mail=mail, account_type='mail', conn=conn)
    if _qr[0] is not False:
        return (False, 'ALREADY_EXISTS')

    # Get @domainAccountSetting.
    qr = ldap_lib_domain.get_profile(domain=domain, conn=conn)

    if not qr[0]:
        return qr

    domain_profile = qr[1]['ldif']
    domain_status = domain_profile.get('accountStatus', ['disabled'])[0]
    domainAccountSetting = ldaputils.get_account_setting_from_profile(domain_profile)

    # Check account number limit.
    _num_users = domainAccountSetting.get('numberOfUsers')
    if _num_users == '-1':
        return (False, 'NOT_ALLOWED')

    _pw_hash = form.get('password_hash', '')
    if _pw_hash:
        if not iredpwd.is_supported_password_scheme(_pw_hash):
            return (False, 'INVALID_PASSWORD_SCHEME')

        passwd_plain = ''
        passwd_hash = _pw_hash
    else:
        (min_pw_len, max_pw_len) = ldap_lib_general.get_domain_password_lengths(
            domain=domain,
            account_settings=domainAccountSetting,
            fallback_to_global_settings=False,
            conn=conn,
        )

        qr = form_utils.get_password(form=form,
                                     input_name='newpw',
                                     confirm_pw_input_name='confirmpw',
                                     min_passwd_length=min_pw_len,
                                     max_passwd_length=max_pw_len)

        if qr[0]:
            passwd_plain = qr[1]['pw_plain']
            passwd_hash = qr[1]['pw_hash']
        else:
            return qr

    cn = form_utils.get_name(form=form, input_name="cn")

    # Get preferred language.
    preferred_language = form_utils.get_language(form=form)
    if preferred_language not in iredutils.get_language_maps():
        preferred_language = None

    # Get user quota. Unit is MB.
    quota = form_utils.get_single_value(form=form,
                                        input_name='mailQuota',
                                        default_value=0,
                                        is_integer=True)

    quota = abs(quota)

    if quota == 0:
        # Get per-domain default user quota
        default_user_quota = ldap_lib_domain.get_default_user_quota(domain=domain,
                                                                    domain_account_setting=domainAccountSetting)

        quota = default_user_quota

    defaultStorageBaseDirectory = domainAccountSetting.get('defaultStorageBaseDirectory', None)

    db_settings = iredutils.get_settings_from_db()
    # Get mailbox format and folder.
    _mailbox_format = form.get('mailboxFormat', '').lower()
    _mailbox_folder = form.get('mailboxFolder', '')
    if not iredutils.is_valid_mailbox_format(_mailbox_format):
        _mailbox_format = db_settings['mailbox_format']

    if not iredutils.is_valid_mailbox_folder(_mailbox_folder):
        _mailbox_folder = db_settings['mailbox_folder']

    # Get full maildir path
    _mailbox_maildir = form.get('maildir')

    # Get default mailing lists which set in domain accountSetting.
    ldif = iredldif.ldif_mailuser(
        domain=domain,
        username=username,
        cn=cn,
        passwd=passwd_hash,
        quota=quota,
        storage_base_directory=defaultStorageBaseDirectory,
        mailbox_format=_mailbox_format,
        mailbox_folder=_mailbox_folder,
        mailbox_maildir=_mailbox_maildir,
        language=preferred_language,
        domain_status=domain_status,
    )

    dn_user = ldaputils.rdn_value_to_user_dn(mail)

    # Store plain password in additional attribute
    if passwd_plain and settings.STORE_PLAIN_PASSWORD_IN_ADDITIONAL_ATTR:
        ldif += [(settings.STORE_PLAIN_PASSWORD_IN_ADDITIONAL_ATTR, [passwd_plain])]

    try:
        conn.add_s(dn_user, ldif)

        # Update count of accounts
        ldap_lib_general.update_num_domain_current_users(domain=domain,
                                                         increase=True,
                                                         conn=conn)

        log_activity(msg="Create user: %s." % (mail), domain=domain, event='create')

        return (True, )
    except ldap.ALREADY_EXISTS:
        return (False, 'ALREADY_EXISTS')
    except Exception as e:
        return (False, repr(e))


@decorators.require_global_admin
def mark_unmark_as_admin(domain, mails, action, conn=None):
    domain = str(domain).lower()
    mails = [str(v).lower()
             for v in mails
             if iredutils.is_email(v) and v.endswith('@' + domain)]

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    result = {}
    for mail in mails:
        dn = ldaputils.rdn_value_to_user_dn(mail)

        if action in ['markasglobaladmin', 'unmarkasglobaladmin']:
            # Require global admin
            if not session.get('is_global_admin'):
                return (False, 'PERMISSION_DENIED')

            update_attribute = 'domainGlobalAdmin'
            update_value = 'yes'
            update_action = 'delete'

            if action == 'markasglobaladmin':
                update_action = 'add'

        try:
            ldap_lib_general.add_or_remove_attr_values(dn=dn,
                                                       attr=update_attribute,
                                                       values=[update_value],
                                                       action=update_action,
                                                       conn=conn)
        except Exception as e:
            result[mail] = str(e)

    if result == {}:
        return (True, )
    else:
        return (False, repr(result))


# Delete single user.
def __delete_single_user(mail,
                         keep_mailbox_days=0,
                         conn=None):
    mail = web.safestr(mail)
    if not iredutils.is_email(mail):
        return (False, 'INVALID_MAIL')

    # Get domain name of this account.
    domain = mail.split('@')[-1]

    # Get dn of mail user and domain.
    dn_user = ldaputils.rdn_value_to_user_dn(mail)

    try:
        keep_mailbox_days = int(keep_mailbox_days)
    except:
        if session.get('is_global_admin'):
            keep_mailbox_days = 0
        else:
            _max_days = max(settings.DAYS_TO_KEEP_REMOVED_MAILBOX)
            if keep_mailbox_days > _max_days:
                # Get the max days
                keep_mailbox_days = _max_days

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    # Log maildir path in SQL table.
    try:
        qr = get_profile(mail=mail, conn=conn)
        if not qr[0]:
            if qr[1] == 'NO_SUCH_ACCOUNT':
                # If destination user doesn't exist, don't waste time to check
                # other data.
                return (True, )

            return qr

        user_profile = qr[1]['ldif']

        if 'homeDirectory' in user_profile:
            maildir = user_profile.get('homeDirectory', [''])[0]
        else:
            storageBaseDirectory = user_profile.get('storageBaseDirectory', [''])[0]
            mailMessageStore = user_profile.get('mailMessageStore', [''])[0]
            maildir = os.path.join(storageBaseDirectory, mailMessageStore)

        if keep_mailbox_days == 0:
            sql_keep_days = None
        else:
            # Convert keep days to string
            _now_in_seconds = time.time()
            _days_in_seconds = _now_in_seconds + (keep_mailbox_days * 24 * 60 * 60)
            sql_keep_days = time.strftime('%Y-%m-%d', time.localtime(_days_in_seconds))

        web.conn_iredadmin.insert(
            'deleted_mailboxes',
            maildir=maildir,
            username=mail,
            domain=domain,
            admin=session.get('username'),
            delete_date=sql_keep_days,
        )
    except:
        pass

    # Delete user object.
    try:
        # Delete object and its subtree.
        _qr = ldap_lib_general.delete_ldap_tree(dn=dn_user, conn=conn)
        if not _qr[0]:
            return _qr

        # Delete record from SQL database: real-time used quota.
        try:
            ldap_lib_general.delete_account_used_quota([mail])
        except:
            pass

        # Log delete action.
        log_activity(msg="Delete user: %s." % (mail),
                     domain=domain,
                     event='delete')

        return (True, )
    except ldap.LDAPError as e:
        return (False, repr(e))


# Delete mail users in same domain.
@decorators.require_global_admin
def delete(domain,
           mails=None,
           keep_mailbox_days=0,
           conn=None):
    if not mails:
        return (False, 'NO_ACCOUNT_SELECTED')

    domain = str(domain).lower()
    mails = [str(v).lower()
             for v in mails
             if iredutils.is_email(v) and str(v).endswith('@' + domain)]

    if not mails:
        return (False, 'INVALID_MAIL')

    if not iredutils.is_domain(domain):
        return (False, 'INVALID_DOMAIN_NAME')

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    try:
        # Remove users from:
        #   - domain admin list
        #   - member of mail alias account
        _filter1 = '(&(objectClass=mailDomain)(|'
        for m in mails:
            _filter1 += '(domainAdmin=%s)' % m
        _filter1 += '))'

        _filter2 = '(&(objectClass=mailAlias)(|'
        for m in mails:
            _filter2 += '(mailForwardingAddress=%s)' % m
        _filter2 += '))'

        _filter = '(|' + _filter1 + _filter2 + ')'

        qr = conn.search_s(settings.ldap_basedn,
                           ldap.SCOPE_SUBTREE,
                           _filter,
                           ['dn', 'objectClass', 'domainAdmin', 'mailForwardingAddress'])

        if qr:
            obj_attr_maps = [('mailDomain', 'domainAdmin'),
                             ('mailAlias', 'mailForwardingAddress')]

            for (_dn, _ldif) in qr:
                _ldif = iredutils.bytes2str(_ldif)
                _objs = _ldif.get('objectClass', [])

                for (_obj, _attr) in obj_attr_maps:
                    if _obj in _objs:
                        _remove_addrs = list(set(mails) & set(_ldif.get(_attr, [])))
                        ldap_lib_general.remove_attr_values(dn=_dn,
                                                            attr=_attr,
                                                            values=_remove_addrs,
                                                            conn=conn)
    except:
        pass

    result = {}
    num_removed = 0
    for m in mails:
        m = web.safestr(m)

        # Delete user object (ldap.SCOPE_BASE).
        qr = __delete_single_user(mail=m,
                                  keep_mailbox_days=keep_mailbox_days,
                                  conn=conn)

        if qr[0]:
            num_removed += 1
        else:
            result[m] = repr(qr[1])

    # Update count of accounts
    if num_removed > 0:
        ldap_lib_general.update_num_domain_current_users(domain=domain,
                                                         decrease=True,
                                                         conn=conn)

    if result == {}:
        return (True, )
    else:
        return (False, repr(result))


@decorators.require_global_admin
def update(profile_type, mail, form, conn=None):
    profile_type = web.safestr(profile_type)
    mail = str(mail).lower()
    (username, domain) = mail.split('@', 1)

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    # Get account dn.
    dn_user = ldaputils.rdn_value_to_user_dn(mail)

    mod_attrs = []

    qr = ldap_lib_general.get_domain_account_setting(domain=domain, conn=conn)
    if qr[0]:
        domainAccountSetting = qr[1]
    else:
        return qr

    qr = get_profile(mail=mail, conn=conn)
    if qr[0]:
        user_profile = qr[1]['ldif']
        user_account_setting = ldaputils.get_account_setting_from_profile(user_profile)
    else:
        return qr

    if profile_type == 'general':
        # Update domainGlobalAdmin=yes
        if session.get('is_global_admin'):
            # Update domainGlobalAdmin=yes
            if 'domainGlobalAdmin' in form:
                mod_attrs = ldaputils.mod_replace('domainGlobalAdmin', 'yes')

                if user_profile.get('domainGlobalAdmin') != ['yes']:
                    log_activity(msg="User %s is marked as global admin." % mail,
                                 username=mail,
                                 domain=domain,
                                 event='grant')
            else:
                mod_attrs = ldaputils.mod_replace('domainGlobalAdmin', None)

                if user_profile.get('domainGlobalAdmin') == ['yes']:
                    log_activity(msg="User %s is not a global admin anymore." % mail,
                                 username=mail,
                                 domain=domain,
                                 event='revoke')

        # Get full name, first name, last name.
        # Note: cn, givenName, sn are required by objectClass `inetOrgPerson`.
        cn = form_utils.get_name(form=form, input_name="cn")
        first_name = form_utils.get_single_value(form=form, input_name="first_name")
        last_name = form_utils.get_single_value(form=form, input_name="last_name")

        mod_attrs += ldaputils.mod_replace(attr="cn",
                                           value=cn,
                                           default=username)

        mod_attrs += ldaputils.mod_replace(attr='givenName',
                                           value=first_name,
                                           default=username)

        mod_attrs += ldaputils.mod_replace(attr='sn',
                                           value=last_name,
                                           default=username)

        # Get preferred language: short lang code. e.g. en_US, de_DE.
        preferred_language = form_utils.get_language(form)
        # Must be equal to or less than 5 characters.
        if not (preferred_language in iredutils.get_language_maps()):
            preferred_language = None

        mod_attrs += ldaputils.mod_replace('preferredLanguage', preferred_language)

        # Update language immediately.
        if session.get('username') == mail and \
           session.get('lang', 'en_US') != preferred_language:
            session['lang'] = preferred_language

        # Update timezone
        tz_name = form_utils.get_timezone(form)

        if qr[0]:
            user_account_setting['timezone'] = tz_name

            if session['username'] == mail and tz_name:
                session['timezone'] = TIMEZONES[tz_name]

        # Update employeeNumber, mobile, title.
        mod_attrs += ldaputils.mod_replace('employeeNumber', form.get('employeeNumber'))

        ############
        # Reset quota
        #
        # Get new mail quota from web form.
        quota = form_utils.get_single_value(form=form,
                                            input_name='mailQuota',
                                            default_value=0,
                                            is_integer=True)

        # quota must be stored in bytes.
        mod_attrs += ldaputils.mod_replace('mailQuota', quota*1024*1024)

        # Get telephoneNumber, mobile.
        # - multi values are allowed.
        # - non-ascii characters are not allowed.
        for k in ['mobile', 'telephoneNumber']:
            mod_attrs += ldaputils.form_mod_attrs_from_api(form=form,
                                                           input_name=k,
                                                           attr=k,
                                                           to_string=True)

        # Get title, with multiple values.
        for _attr in ['title']:
            _values = [v for v in form.get(_attr, []) if v]

            # Remove duplicate entries
            _values = list(set(_values))

            mod_attrs += ldaputils.mod_replace(attr=_attr, value=_values)

        # check account status.
        accountStatus = 'disabled'
        if 'accountStatus' in form:
            accountStatus = 'active'
        mod_attrs += ldaputils.mod_replace('accountStatus', accountStatus)

    elif profile_type == 'password':
        # Get password length from @domainAccountSetting.
        (min_pw_len, max_pw_len) = ldap_lib_general.get_domain_password_lengths(domain=domain,
                                                                                account_settings=domainAccountSetting,
                                                                                fallback_to_global_settings=False,
                                                                                conn=conn)

        # Get new passwords from user input.
        newpw = web.safestr(form.get('newpw', ''))
        confirmpw = web.safestr(form.get('confirmpw', ''))

        result = iredpwd.verify_new_password(newpw=newpw,
                                             confirmpw=confirmpw,
                                             min_passwd_length=min_pw_len,
                                             max_passwd_length=max_pw_len)

        if result[0] is True:
            if 'store_password_in_plain_text' in form and settings.STORE_PASSWORD_IN_PLAIN_TEXT:
                passwd = iredpwd.generate_password_hash(result[1], pwscheme='PLAIN')
            else:
                passwd = iredpwd.generate_password_hash(result[1])

            mod_attrs += ldaputils.mod_replace('userPassword', passwd)
            mod_attrs += ldaputils.mod_replace('shadowLastChange', ldaputils.get_days_of_shadow_last_change())

            # Always store plain password in another attribute.
            if settings.STORE_PLAIN_PASSWORD_IN_ADDITIONAL_ATTR:
                mod_attrs += ldaputils.mod_replace(settings.STORE_PLAIN_PASSWORD_IN_ADDITIONAL_ATTR, newpw)
        else:
            return result

    # accountSetting
    list_of_account_setting = ldaputils.account_setting_dict_to_list(user_account_setting)
    mod_attrs += ldaputils.mod_replace('accountSetting', list_of_account_setting)

    try:
        conn.modify_s(dn_user, mod_attrs)

        log_activity(msg="Update user profile ({}): {}.".format(profile_type, mail),
                     admin=session.get('username'),
                     username=mail,
                     domain=domain,
                     event='update')

        return (True, {})
    except Exception as e:
        return (False, repr(e))


def __mark_user_as_admin(user, domains, conn=None):
    user = str(user).lower()
    if not iredutils.is_email(user):
        return (False, 'INVALID_MAIL')

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    for i in domains:
        domain_dn = ldaputils.rdn_value_to_domain_dn(i)
        try:
            qr = ldap_lib_general.add_attr_values(dn=domain_dn,
                                                  attr='domainAdmin',
                                                  values=[user],
                                                  conn=conn)
            if not qr[0]:
                return qr

        except Exception as e:
            return (False, repr(e))

    return (True, )


def __unmark_user_as_admin(user, domains=None, all_domains=False, conn=None):
    user = str(user).lower()
    if not iredutils.is_email(user):
        return (False, 'INVALID_MAIL')

    if not conn:
        _wrap = LDAPWrap()
        conn = _wrap.conn

    if domains:
        try:
            for d in domains:
                domain_dn = ldaputils.rdn_value_to_domain_dn(d)
                qr = ldap_lib_general.remove_attr_values(dn=domain_dn,
                                                         attr='domainAdmin',
                                                         values=[user],
                                                         conn=conn)
                if not qr[0]:
                    return qr

            return (True, )
        except Exception as e:
            return (False, repr(e))
    else:
        if all_domains:
            # Remove this user admin from all domains by default.
            qr_filter = '(&(objectClass=mailDomain)(domainAdmin=%s))' % user

            qr = conn.search_s(settings.ldap_basedn,
                               ldap.SCOPE_ONELEVEL,
                               qr_filter,
                               ['dn'])

            for (dn, _ldif) in qr:
                try:
                    ldap_lib_general.remove_attr_values(dn=dn,
                                                        attr='domainAdmin',
                                                        values=[user],
                                                        conn=conn)
                except Exception as e:
                    return (False, repr(e))

        return (True, )
