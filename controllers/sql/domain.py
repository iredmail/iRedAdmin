# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings

from libs import iredutils, form_utils
from libs.l10n import TIMEZONES

from libs.sqllib import SQLWrap, decorators, sqlutils
from libs.sqllib import domain as sql_lib_domain
from libs.sqllib import admin as sql_lib_admin

session = web.config.get('_session')


class List:
    @decorators.require_global_admin
    def GET(self, cur_page=1, disabled_only=False):
        """List paged mail domains."""
        form = web.input(_unicode=False)
        cur_page = int(cur_page) or 1

        all_domain_profiles = []
        domain_used_quota = {}
        all_first_chars = []

        first_char = None
        if 'starts_with' in form:
            first_char = form.get('starts_with')[:1].upper()
            if not iredutils.is_valid_account_first_char(first_char):
                first_char = None

        _wrap = SQLWrap()
        conn = _wrap.conn

        # Get first characters of all domains
        _qr = sql_lib_domain.get_first_char_of_all_domains(conn=conn)
        if _qr[0]:
            all_first_chars = _qr[1]

        total = sql_lib_admin.num_managed_domains(conn=conn,
                                                  disabled_only=disabled_only,
                                                  first_char=first_char)

        if total:
            qr = sql_lib_domain.get_paged_domains(cur_page=cur_page,
                                                  first_char=first_char,
                                                  disabled_only=disabled_only,
                                                  conn=conn)
            if qr[0]:
                all_domain_profiles = qr[1]

            if settings.SHOW_USED_QUOTA:
                domains = []
                for i in all_domain_profiles:
                    domains.append(str(i.domain))

                domain_used_quota = sql_lib_domain.get_domain_used_quota(conn=conn,
                                                                         domains=domains)

        if session.get('is_global_admin'):
            days_to_keep_removed_mailbox = settings.DAYS_TO_KEEP_REMOVED_MAILBOX_FOR_GLOBAL_ADMIN
        else:
            days_to_keep_removed_mailbox = settings.DAYS_TO_KEEP_REMOVED_MAILBOX

        return web.render('sql/domain/list.html',
                          cur_page=cur_page,
                          total=total,
                          all_domain_profiles=all_domain_profiles,
                          domain_used_quota=domain_used_quota,
                          local_transports=settings.LOCAL_TRANSPORTS,
                          first_char=first_char,
                          all_first_chars=all_first_chars,
                          disabled_only=disabled_only,
                          days_to_keep_removed_mailbox=days_to_keep_removed_mailbox,
                          msg=form.get('msg', None))

    @decorators.require_global_admin
    @decorators.csrf_protected
    def POST(self):
        form = web.input(domainName=[], _unicode=False)
        domains = form.get('domainName', [])
        action = form.get('action')

        if action not in ['delete', 'enable', 'disable']:
            raise web.seeother('/domains?msg=INVALID_ACTION')

        _wrap = SQLWrap()
        conn = _wrap.conn

        if not domains:
            raise web.seeother('/domains?msg=INVALID_DOMAIN_NAME')

        if action == 'delete':
            keep_mailbox_days = form_utils.get_single_value(form=form,
                                                            input_name='keep_mailbox_days',
                                                            default_value=0,
                                                            is_integer=True)

            qr = sql_lib_domain.delete_domains(domains=domains,
                                               keep_mailbox_days=keep_mailbox_days,
                                               conn=conn)
            msg = 'DELETED'

        elif action in ['enable', 'disable']:
            qr = sql_lib_domain.enable_disable_domains(domains=domains,
                                                       action=action,
                                                       conn=conn)

            # msg: ENABLED, DISABLED
            msg = action.upper() + 'D'
        else:
            raise web.seeother('/domains?msg=INVALID_ACTION')

        if qr[0]:
            raise web.seeother('/domains?msg=%s' % msg)
        else:
            raise web.seeother('/domains?msg=' + web.urlquote(qr[1]))


class ListDisabled:
    """List disabled mail domains."""
    @decorators.require_global_admin
    def GET(self, cur_page=1):
        lst = List()
        return lst.GET(cur_page=cur_page, disabled_only=True)


class Profile:
    @decorators.require_global_admin
    def GET(self, profile_type, domain):
        form = web.input()
        domain = web.safestr(domain.split('/', 1)[0])
        profile_type = web.safestr(profile_type)

        _wrap = SQLWrap()
        conn = _wrap.conn

        result = sql_lib_domain.profile(conn=conn, domain=domain)

        if result[0] is not True:
            raise web.seeother('/domains?msg=' + web.urlquote(result[1]))

        domain_profile = result[1]

        # Get settings from db.
        _settings = iredutils.get_settings_from_db(params=['min_passwd_length', 'max_passwd_length'])
        global_min_passwd_length = _settings['min_passwd_length']
        global_max_passwd_length = _settings['max_passwd_length']

        return web.render(
            'sql/domain/profile.html',
            cur_domain=domain,
            profile_type=profile_type,
            profile=domain_profile,
            default_mta_transport=settings.default_mta_transport,
            domain_settings=sqlutils.account_settings_string_to_dict(domain_profile['settings']),
            global_min_passwd_length=global_min_passwd_length,
            global_max_passwd_length=global_max_passwd_length,
            timezones=TIMEZONES,
            # Language
            languagemaps=iredutils.get_language_maps(),
            msg=form.get('msg'),
        )

    @decorators.csrf_protected
    @decorators.require_global_admin
    def POST(self, profile_type, domain):
        domain = str(domain).lower()

        form = web.input()
        result = sql_lib_domain.update(profile_type=profile_type,
                                       domain=domain,
                                       form=form)

        if result[0] is True:
            raise web.seeother('/profile/domain/{}/{}?msg=UPDATED'.format(profile_type, domain))
        else:
            raise web.seeother('/profile/domain/{}/{}?msg={}'.format(profile_type, domain, web.urlquote(result[1])))


class Create:
    @decorators.require_global_admin
    def GET(self):
        form = web.input()

        return web.render('sql/domain/create.html',
                          preferred_language=settings.default_language,
                          languagemaps=iredutils.get_language_maps(),
                          timezones=TIMEZONES,
                          msg=form.get('msg'))

    @decorators.require_global_admin
    @decorators.csrf_protected
    def POST(self):
        form = web.input()
        domain = form_utils.get_domain_name(form)

        result = sql_lib_domain.add(form=form)

        if result[0] is True:
            raise web.seeother('/profile/domain/general/%s?msg=CREATED' % domain)
        else:
            raise web.seeother('/create/domain?msg=%s' % web.urlquote(result[1]))
