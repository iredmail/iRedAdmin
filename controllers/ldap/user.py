# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings

from libs import iredutils, form_utils
from libs.l10n import TIMEZONES
from libs.ldaplib.core import LDAPWrap
from libs.ldaplib import decorators, ldaputils
from libs.ldaplib import domain as ldap_lib_domain
from libs.ldaplib import user as ldap_lib_user
from libs.ldaplib import general as ldap_lib_general

session = web.config.get('_session')


# User related.
class Users:
    @decorators.require_global_admin
    def GET(self, domain, cur_page=1, disabled_only=False):
        domain = web.safestr(domain)
        cur_page = int(cur_page)

        form = web.input()

        order_name = form.get('order_name')

        # Currently only sorting by `name` and `quota` are supported.
        if order_name not in ["name", "quota"]:
            order_name = "name"

        order_by_desc = (form.get('order_by', 'asc').lower() == 'desc')

        first_char = None
        search_filter = None
        if 'starts_with' in form:
            first_char = form.get('starts_with')[:1].upper()

            if iredutils.is_valid_account_first_char(first_char):
                search_filter = '(&(objectClass=mailUser)(mail=%s*))' % first_char

        _wrap = LDAPWrap()
        conn = _wrap.conn

        qr = ldap_lib_user.list_accounts(domain=domain,
                                         search_filter=search_filter,
                                         disabled_only=disabled_only,
                                         conn=conn)

        if not qr[0]:
            raise web.seeother('/domains?msg=%s' % web.urlquote(qr[1]))

        all_users = qr[1]
        sl = ldap_lib_general.get_paged_account_list(account_profiles=all_users,
                                                     current_page=cur_page,
                                                     domain=domain,
                                                     account_type='user',
                                                     order_name=order_name,
                                                     order_by_desc=order_by_desc,
                                                     conn=conn)

        account_profiles = sl['account_profiles']

        # Get real-time used quota.
        used_quotas = {}

        if settings.SHOW_USED_QUOTA:
            # Get email address list.
            accountEmailLists = []
            for tmpuser in account_profiles:
                accountEmailLists += tmpuser[1].get('mail', [])

            if len(accountEmailLists) > 0:
                used_quotas = ldap_lib_general.get_account_used_quota(accountEmailLists)

        if cur_page > sl['pages']:
            cur_page = sl['pages']

        if session.get('is_global_admin'):
            days_to_keep_removed_mailbox = settings.DAYS_TO_KEEP_REMOVED_MAILBOX_FOR_GLOBAL_ADMIN
        else:
            days_to_keep_removed_mailbox = settings.DAYS_TO_KEEP_REMOVED_MAILBOX

        all_first_chars = ldap_lib_general.get_first_char_of_all_accounts(domain=domain,
                                                                          account_type='user',
                                                                          conn=conn)

        return web.render('ldap/user/list.html',
                          cur_page=cur_page,
                          total=sl['total'],
                          users=account_profiles,
                          cur_domain=domain,
                          used_quotas=used_quotas,
                          order_name=order_name,
                          order_by_desc=order_by_desc,
                          all_first_chars=all_first_chars,
                          first_char=first_char,
                          disabled_only=disabled_only,
                          days_to_keep_removed_mailbox=days_to_keep_removed_mailbox,
                          msg=form.get('msg'))

    # Delete users.
    @decorators.csrf_protected
    @decorators.require_global_admin
    def POST(self, domain, page=1):
        form = web.input(_unicode=False, mail=[])
        page = int(page)
        if page < 1:
            page = 1

        domain = str(domain).lower()
        mails = form.get('mail', [])
        action = form.get('action', None)

        mails = [str(v).lower()
                 for v in mails
                 if iredutils.is_email(v) and str(v).endswith('@' + str(domain))]

        if action == 'delete':
            keep_mailbox_days = form_utils.get_single_value(form=form,
                                                            input_name='keep_mailbox_days',
                                                            default_value=0,
                                                            is_integer=True)

            result = ldap_lib_user.delete(domain=domain,
                                          mails=mails,
                                          keep_mailbox_days=keep_mailbox_days,
                                          conn=None)
            msg = 'DELETED'
        elif action == 'disable':
            result = ldap_lib_general.enable_disable_users(mails=mails, action='disable', conn=None)
            msg = 'DISABLED'
        elif action == 'enable':
            result = ldap_lib_general.enable_disable_users(mails=mails, action='enable', conn=None)
            msg = 'ENABLED'
        elif action in ['markasglobaladmin', 'unmarkasglobaladmin']:
            result = ldap_lib_user.mark_unmark_as_admin(domain=domain, mails=mails, action=action, conn=None)
            msg = action.upper()
        else:
            result = (False, 'INVALID_ACTION')
            msg = form.get('msg', None)

        if result[0] is True:
            raise web.seeother('/users/%s/page/%d?msg=%s' % (domain, page, msg))
        else:
            raise web.seeother('/users/%s/page/%d?msg=%s' % (domain, page, web.urlquote(result[1])))


class DisabledUsers:
    @decorators.require_global_admin
    def GET(self, domain, cur_page=1):
        _users = Users()
        return _users.GET(domain=domain, cur_page=cur_page, disabled_only=True)


class Profile:
    @decorators.require_global_admin
    def GET(self, profile_type, mail):
        mail = str(mail).lower()
        cur_domain = mail.split('@', 1)[-1]

        form = web.input(enabledService=[], telephoneNumber=[], domainName=[])
        msg = form.get('msg')

        profile_type = web.safestr(profile_type)

        _wrap = LDAPWrap()
        conn = _wrap.conn

        qr = ldap_lib_user.get_profile(mail=mail, conn=conn)
        if not qr[0]:
            raise web.seeother('/users/{}?msg={}'.format(cur_domain, web.urlquote(qr[1])))

        user_profile = qr[1]['ldif']
        user_account_setting = ldaputils.account_setting_list_to_dict(user_profile.get('accountSetting', []))

        # profile_type == 'general'
        accountUsedQuota = {}

        # Per-domain account settings
        domainAccountSetting = {}

        # Get accountSetting of current domain.
        qr = ldap_lib_general.get_domain_account_setting(domain=cur_domain, conn=conn)
        if qr[0] is True:
            domainAccountSetting = qr[1]

        if profile_type == 'general':
            # Get account used quota.
            if settings.SHOW_USED_QUOTA:
                accountUsedQuota = ldap_lib_general.get_account_used_quota([mail])

        (min_passwd_length, max_passwd_length) = ldap_lib_general.get_domain_password_lengths(domain=cur_domain,
                                                                                              account_settings=domainAccountSetting,
                                                                                              fallback_to_global_settings=False)

        password_policies = iredutils.get_password_policies()
        if min_passwd_length > 0:
            password_policies['min_passwd_length'] = min_passwd_length

        if max_passwd_length > 0:
            password_policies['max_passwd_length'] = max_passwd_length

        return web.render(
            'ldap/user/profile.html',
            profile_type=profile_type,
            mail=mail,
            user_profile=user_profile,
            user_account_setting=user_account_setting,
            defaultStorageBaseDirectory=settings.storage_base_directory,
            timezones=TIMEZONES,
            min_passwd_length=min_passwd_length,
            max_passwd_length=max_passwd_length,
            store_password_in_plain_text=settings.STORE_PASSWORD_IN_PLAIN_TEXT,
            password_policies=iredutils.get_password_policies(),
            accountUsedQuota=accountUsedQuota,
            domainAccountSetting=domainAccountSetting,
            languagemaps=iredutils.get_language_maps(),
            msg=msg,
        )

    @decorators.require_global_admin
    @decorators.csrf_protected
    def POST(self, profile_type, mail):
        mail = str(mail).lower()
        domain = mail.split('@', 1)[-1]

        _wrap = LDAPWrap()
        conn = _wrap.conn

        # - Allow global admin
        # - normal admin who manages this domain
        # - allow normal admin who doesn't manage this domain, but is updating its own profile
        if not ldap_lib_general.is_domain_admin(domain=domain, admin=session.get('username'), conn=conn):
            raise web.seeother('/domains?msg=PERMISSION_DENIED')

        form = web.input(
            domainName=[],      # Managed domains
            oldDomainName=[],   # Old managed domains
            enabledService=[],
            mobile=[],
            title=[],
            telephoneNumber=[],
        )

        result = ldap_lib_user.update(profile_type=profile_type,
                                      mail=mail,
                                      form=form,
                                      conn=conn)

        if result[0]:
            raise web.seeother('/profile/user/{}/{}?msg=UPDATED'.format(profile_type, mail))
        else:
            raise web.seeother('/profile/user/{}/{}?msg={}'.format(profile_type, mail, web.urlquote(result[1])))


class Create:
    @decorators.require_global_admin
    def GET(self, domain):
        domain = str(domain).lower()
        form = web.input()

        _wrap = LDAPWrap()
        conn = _wrap.conn

        _attrs = ['domainName', 'accountSetting', 'domainCurrentQuotaSize']
        result = ldap_lib_domain.list_accounts(attributes=_attrs, conn=conn)
        if result[0] is True:
            allDomains = result[1]

            # Get accountSetting of current domain.
            allAccountSettings = ldaputils.get_account_settings_from_qr(allDomains)
            domainAccountSetting = allAccountSettings.get(domain, {})

            defaultUserQuota = ldap_lib_domain.get_default_user_quota(domain=domain,
                                                                      domain_account_setting=domainAccountSetting)
        else:
            raise web.seeother('/domains?msg=' + web.urlquote(result[1]))

        # Get number of account limit.
        numberOfCurrentAccounts = ldap_lib_general.num_users_under_domain(domain=domain, conn=conn)

        (min_passwd_length, max_passwd_length) = ldap_lib_general.get_domain_password_lengths(
            domain=domain,
            account_settings=domainAccountSetting,
            fallback_to_global_settings=True,
        )

        return web.render('ldap/user/create.html',
                          cur_domain=domain,
                          allDomains=allDomains,
                          defaultUserQuota=defaultUserQuota,
                          domainAccountSetting=domainAccountSetting,
                          min_passwd_length=min_passwd_length,
                          max_passwd_length=max_passwd_length,
                          store_password_in_plain_text=settings.STORE_PASSWORD_IN_PLAIN_TEXT,
                          password_policies=iredutils.get_password_policies(),
                          numberOfCurrentAccounts=numberOfCurrentAccounts,
                          languagemaps=iredutils.get_language_maps(),
                          msg=form.get('msg'))

    @decorators.csrf_protected
    @decorators.require_global_admin
    def POST(self, domain):
        domain = str(domain).lower()
        form = web.input()

        domain_in_form = form_utils.get_domain_name(form)
        if domain != domain_in_form:
            raise web.seeother('/domains?msg=PERMISSION_DENIED')

        # Get username, cn.
        username = form_utils.get_single_value(form, input_name='username', to_string=True)

        result = ldap_lib_user.add(domain=domain, form=form, conn=None)
        if result[0] is True:
            raise web.seeother('/profile/user/general/%s?msg=CREATED' % (username + '@' + domain))
        else:
            raise web.seeother('/create/user/{}?msg={}'.format(domain, web.urlquote(result[1])))
