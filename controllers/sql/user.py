# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings

from libs import iredutils, form_utils
from libs.l10n import TIMEZONES

from libs.sqllib import SQLWrap, decorators, sqlutils
from libs.sqllib import user as sql_lib_user
from libs.sqllib import admin as sql_lib_admin
from libs.sqllib import domain as sql_lib_domain
from libs.sqllib import utils as sql_lib_utils
from libs.sqllib import general as sql_lib_general

session = web.config.get('_session')


class List:
    @decorators.require_global_admin
    def GET(self, domain, cur_page=1, disabled_only=False):
        domain = str(domain).lower()
        cur_page = int(cur_page) or 1

        form = web.input(_unicode=False)

        order_name = form.get('order_name')

        # Currently only sorting by `name` and `quota` are supported.
        if order_name not in ["name", "quota"]:
            order_name = "name"

        order_by_desc = (form.get('order_by', 'asc').lower() == 'desc')

        records = []

        # Real-time used quota.
        used_quotas = {}

        all_first_chars = []
        first_char = None
        if 'starts_with' in form:
            first_char = form.get('starts_with')[:1].upper()
            if not iredutils.is_valid_account_first_char(first_char):
                first_char = None

        _wrap = SQLWrap()
        conn = _wrap.conn

        total = sql_lib_user.num_users_under_domains(conn=conn,
                                                     domains=[domain],
                                                     disabled_only=disabled_only,
                                                     first_char=first_char)

        if total:
            _qr = sql_lib_general.get_first_char_of_all_accounts(domain=domain,
                                                                 account_type='user',
                                                                 conn=conn)
            if _qr[0]:
                all_first_chars = _qr[1]

            qr = sql_lib_user.get_paged_users(conn=conn,
                                              domain=domain,
                                              cur_page=cur_page,
                                              order_name=order_name,
                                              order_by_desc=order_by_desc,
                                              first_char=first_char,
                                              disabled_only=disabled_only)

            if qr[0]:
                records = qr[1]
            else:
                raise web.seeother('/domains?msg=%s' % web.urlquote(qr[1]))

            # Get list of email addresses
            mails = []
            for r in records:
                mails += [str(r.get('username')).lower()]

            if mails:
                # Get real-time mailbox usage
                if settings.SHOW_USED_QUOTA:
                    try:
                        used_quotas = sql_lib_general.get_account_used_quota(accounts=mails, conn=conn)
                    except Exception:
                        pass

        if session.get('is_global_admin'):
            days_to_keep_removed_mailbox = settings.DAYS_TO_KEEP_REMOVED_MAILBOX_FOR_GLOBAL_ADMIN
        else:
            days_to_keep_removed_mailbox = settings.DAYS_TO_KEEP_REMOVED_MAILBOX

        return web.render('sql/user/list.html',
                          cur_domain=domain,
                          cur_page=cur_page,
                          total=total,
                          users=records,
                          used_quotas=used_quotas,
                          order_name=order_name,
                          order_by_desc=order_by_desc,
                          all_first_chars=all_first_chars,
                          first_char=first_char,
                          disabled_only=disabled_only,
                          days_to_keep_removed_mailbox=days_to_keep_removed_mailbox,
                          msg=form.get('msg', None))

    @decorators.csrf_protected
    @decorators.require_global_admin
    def POST(self, domain, page=1):
        form = web.input(_unicode=False, mail=[])
        page = int(page)
        if page < 1:
            page = 1

        domain = str(domain).lower()

        # Filter users not under the same domain.
        mails = [str(v)
                 for v in form.get('mail', [])
                 if iredutils.is_email(v) and str(v).endswith('@' + domain)]

        action = form.get('action', None)
        msg = form.get('msg', None)

        redirect_to_admin_list = False
        if 'redirect_to_admin_list' in form:
            redirect_to_admin_list = True

        _wrap = SQLWrap()
        conn = _wrap.conn

        if action == 'delete':
            keep_mailbox_days = form_utils.get_single_value(form=form,
                                                            input_name='keep_mailbox_days',
                                                            default_value=0,
                                                            is_integer=True)
            result = sql_lib_user.delete_users(conn=conn,
                                               accounts=mails,
                                               keep_mailbox_days=keep_mailbox_days)
            msg = 'DELETED'
        elif action == 'disable':
            result = sql_lib_utils.set_account_status(conn=conn,
                                                      accounts=mails,
                                                      account_type='user',
                                                      enable_account=False)
            msg = 'DISABLED'
        elif action == 'enable':
            result = sql_lib_utils.set_account_status(conn=conn,
                                                      accounts=mails,
                                                      account_type='user',
                                                      enable_account=True)
            msg = 'ENABLED'
        elif action == 'markasglobaladmin':
            result = sql_lib_user.mark_user_as_admin(conn=conn,
                                                     domain=domain,
                                                     users=mails,
                                                     as_global_admin=True)
            msg = 'MARKASGLOBALADMIN'
        elif action == 'unmarkasglobaladmin':
            result = sql_lib_user.mark_user_as_admin(conn=conn,
                                                     domain=domain,
                                                     users=mails,
                                                     as_global_admin=False)
            msg = 'UNMARKASGLOBALADMIN'
        else:
            result = (False, 'INVALID_ACTION')

        if result[0] is True:
            if redirect_to_admin_list:
                raise web.seeother('/admins/%s/page/%d?msg=%s' % (domain, page, msg))
            else:
                raise web.seeother('/users/%s/page/%d?msg=%s' % (domain, page, msg))
        else:
            if redirect_to_admin_list:
                raise web.seeother('/admins/%s/page/%d?msg=%s' % (domain, page, web.urlquote(result[1])))
            else:
                raise web.seeother('/users/%s/page/%d?msg=%s' % (domain, page, web.urlquote(result[1])))


class ListDisabled:
    @decorators.require_global_admin
    def GET(self, domain, cur_page=1):
        _instance = List()
        return _instance.GET(domain=domain, cur_page=cur_page, disabled_only=True)


class Profile:
    @decorators.require_global_admin
    def GET(self, profile_type, mail):
        mail = str(mail).lower()
        domain = mail.split('@', 1)[-1]

        _wrap = SQLWrap()
        conn = _wrap.conn

        form = web.input()
        msg = form.get('msg', '')

        # profile_type == 'general'
        used_quota = {}

        qr = sql_lib_user.profile(mail=mail, conn=conn)
        if qr[0]:
            user_profile = qr[1]
        else:
            raise web.seeother('/users/{}?msg={}'.format(domain, web.urlquote(qr[1])))
        del qr

        # Get per-user settings
        user_settings = {}
        qr = sql_lib_general.get_user_settings(conn=conn,
                                               mail=mail,
                                               existing_settings=user_profile['settings'])
        if qr[0]:
            user_settings = qr[1]
        del qr

        # Get used quota.
        if settings.SHOW_USED_QUOTA:
            used_quota = sql_lib_general.get_account_used_quota(accounts=[mail], conn=conn)

        # Get per-domain disabled user profiles.
        qr = sql_lib_domain.simple_profile(conn=conn,
                                           domain=domain,
                                           columns=['settings'])

        if qr[0]:
            domain_profile = qr[1]
            domain_settings = sqlutils.account_settings_string_to_dict(domain_profile['settings'])

            min_passwd_length = domain_settings.get('min_passwd_length', settings.min_passwd_length)
            max_passwd_length = domain_settings.get('max_passwd_length', settings.max_passwd_length)

        return web.render(
            'sql/user/profile.html',
            cur_domain=domain,
            mail=mail,
            profile_type=profile_type,
            profile=user_profile,
            timezones=TIMEZONES,
            min_passwd_length=min_passwd_length,
            max_passwd_length=max_passwd_length,
            store_password_in_plain_text=settings.STORE_PASSWORD_IN_PLAIN_TEXT,
            password_policies=iredutils.get_password_policies(),
            user_settings=user_settings,
            used_quota=used_quota,
            languagemaps=iredutils.get_language_maps(),
            msg=msg,
        )

    @decorators.require_global_admin
    @decorators.csrf_protected
    def POST(self, profile_type, mail):
        form = web.input(
            enabledService=[],
            shadowAddress=[],
            telephoneNumber=[],
            domainName=[],      # Managed domains
        )

        mail = str(mail).lower()

        _wrap = SQLWrap()
        conn = _wrap.conn

        result = sql_lib_user.update(conn=conn,
                                     mail=mail,
                                     profile_type=profile_type,
                                     form=form)

        if result[0]:
            raise web.seeother('/profile/user/{}/{}?msg=UPDATED'.format(profile_type, mail))
        else:
            raise web.seeother('/profile/user/{}/{}?msg={}'.format(profile_type, mail, web.urlquote(result[1])))


class Create:
    @decorators.require_global_admin
    def GET(self, domain):
        domain = str(domain).lower()

        form = web.input()

        # Get all managed domains.
        _wrap = SQLWrap()
        conn = _wrap.conn

        if session.get('is_global_admin'):
            qr = sql_lib_domain.get_all_domains(conn=conn, name_only=True)
        else:
            qr = sql_lib_admin.get_managed_domains(conn=conn,
                                                   admin=session.get('username'),
                                                   domain_name_only=True)

        if qr[0] is True:
            all_domains = qr[1]
        else:
            raise web.seeother('/domains?msg=' + web.urlquote(qr[1]))

        # Get domain profile.
        qr_profile = sql_lib_domain.simple_profile(domain=domain, conn=conn)
        if qr_profile[0] is True:
            domain_profile = qr_profile[1]
            domain_settings = sqlutils.account_settings_string_to_dict(domain_profile['settings'])
        else:
            raise web.seeother('/domains?msg=%s' % web.urlquote(qr_profile[1]))

        # Cet total number and allocated quota size of existing users under domain.
        num_users_under_domain = sql_lib_general.num_users_under_domain(domain=domain, conn=conn)

        min_passwd_length = domain_settings.get('min_passwd_length', settings.min_passwd_length)
        max_passwd_length = domain_settings.get('max_passwd_length', settings.max_passwd_length)

        return web.render(
            'sql/user/create.html',
            cur_domain=domain,
            allDomains=all_domains,
            profile=domain_profile,
            domain_settings=domain_settings,
            min_passwd_length=min_passwd_length,
            max_passwd_length=max_passwd_length,
            store_password_in_plain_text=settings.STORE_PASSWORD_IN_PLAIN_TEXT,
            num_existing_users=num_users_under_domain,
            languagemaps=iredutils.get_language_maps(),
            password_policies=iredutils.get_password_policies(),
            msg=form.get('msg'),
        )

    @decorators.csrf_protected
    @decorators.require_global_admin
    def POST(self, domain):
        domain = str(domain).lower()
        form = web.input()

        domain_in_form = form_utils.get_domain_name(form)
        if domain != domain_in_form:
            raise web.seeother('/domains?msg=PERMISSION_DENIED')

        # Get domain name, username, cn.
        username = form_utils.get_single_value(form,
                                               input_name='username',
                                               to_string=True)

        qr = sql_lib_user.add_user_from_form(domain=domain, form=form)

        if qr[0]:
            raise web.seeother('/profile/user/general/{}@{}?msg=CREATED'.format(username, domain))
        else:
            raise web.seeother('/create/user/{}?msg={}'.format(domain, web.urlquote(qr[1])))
