# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings

from libs import iredutils, form_utils
from libs.l10n import TIMEZONES

from libs.ldaplib.core import LDAPWrap
from libs.ldaplib import decorators, ldaputils
from libs.ldaplib import domain as ldap_lib_domain
from libs.ldaplib import general as ldap_lib_general

session = web.config.get('_session')


# List all virtual mail domains.
class List:
    @decorators.require_global_admin
    def GET(self, cur_page=1, disabled_only=False):
        form = web.input()
        cur_page = int(cur_page)

        if cur_page == 0:
            cur_page = 1

        first_char = None
        all_first_chars = []
        search_filter = None
        if 'starts_with' in form:
            first_char = form.get('starts_with')[:1].upper()
            if not iredutils.is_valid_account_first_char(first_char):
                first_char = None

        _wrap = LDAPWrap()
        conn = _wrap.conn

        qr = ldap_lib_domain.list_accounts(search_filter=search_filter,
                                           disabled_only=disabled_only,
                                           starts_with=first_char,
                                           conn=conn)
        if not qr[0]:
            return qr

        all_domains = qr[1]

        # Get value of accountSetting.
        all_account_settings = ldaputils.get_account_settings_from_qr(all_domains)

        # Get first characters of all domains
        _qr = ldap_lib_domain.get_first_char_of_all_domains(conn=conn)
        if _qr[0]:
            all_first_chars = _qr[1]

        sl = ldap_lib_general.get_paged_account_list(all_domains,
                                                     current_page=cur_page,
                                                     account_type='domain',
                                                     conn=conn)

        if cur_page > sl['pages']:
            cur_page = sl['pages']

        # Get used quota of each domain.
        domain_used_quota = {}
        _all_domain_names = []
        if settings.SHOW_USED_QUOTA:
            for (_dn, _ldif) in all_domains:
                _all_domain_names += _ldif.get('domainName', [])

            domain_used_quota = ldap_lib_general.get_domain_used_quota(domains=_all_domain_names)

        if session.get('is_global_admin'):
            days_to_keep_removed_mailbox = settings.DAYS_TO_KEEP_REMOVED_MAILBOX_FOR_GLOBAL_ADMIN
        else:
            days_to_keep_removed_mailbox = settings.DAYS_TO_KEEP_REMOVED_MAILBOX

        return web.render('ldap/domain/list.html',
                          cur_page=cur_page,
                          total=sl['total'],
                          allDomains=sl['account_profiles'],
                          allAccountSettings=all_account_settings,
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
        action = form.get('action', None)

        if not domains:
            raise web.seeother('/domains?msg=INVALID_DOMAIN_NAME')

        if action == 'delete':
            keep_mailbox_days = form_utils.get_single_value(form=form,
                                                            input_name='keep_mailbox_days',
                                                            default_value=0,
                                                            is_integer=True)

            result = ldap_lib_domain.delete_domains(domains=domains,
                                                    keep_mailbox_days=keep_mailbox_days)
            msg = 'DELETED'
        elif action == 'disable':
            result = ldap_lib_domain.enable_disable_domains(domains=domains, action='disable')
            msg = 'DISABLED'
        elif action == 'enable':
            result = ldap_lib_domain.enable_disable_domains(domains=domains, action='enable')
            msg = 'ENABLED'
        else:
            result = (False, 'INVALID_ACTION')
            msg = form.get('msg', None)

        if result[0] is True:
            raise web.seeother('/domains?msg=%s' % msg)
        else:
            raise web.seeother('/domains?msg=' + web.urlquote(result[1]))


class ListDisabled:
    @decorators.require_global_admin
    def GET(self, cur_page=1):
        _list = List()
        return _list.GET(cur_page=cur_page, disabled_only=True)


class Profile:
    @decorators.require_global_admin
    def GET(self, profile_type, domain):
        form = web.input()
        domain = web.safestr(domain).lower()

        _wrap = LDAPWrap()
        conn = _wrap.conn

        qr = ldap_lib_domain.get_profile(domain=domain, conn=conn)

        if not qr[0]:
            raise web.seeother('/domains?msg=' + web.urlquote(qr[1]))

        domain_profile = qr[1]['ldif']

        r = ldap_lib_domain.list_accounts(attributes=['domainName'], conn=conn)
        if r[0] is True:
            all_domains = r[1]
        else:
            return r

        domain_account_settings = ldaputils.get_account_setting_from_profile(domain_profile)

        (min_passwd_length, max_passwd_length) = ldap_lib_general.get_domain_password_lengths(domain=domain,
                                                                                              account_settings=domain_account_settings,
                                                                                              fallback_to_global_settings=False)

        # Get settings from db.
        _settings = iredutils.get_settings_from_db(params=['min_passwd_length', 'max_passwd_length'])
        global_min_passwd_length = _settings['min_passwd_length']
        global_max_passwd_length = _settings['max_passwd_length']

        return web.render(
            'ldap/domain/profile.html',
            cur_domain=domain,
            allDomains=all_domains,
            domain_account_settings=domain_account_settings,
            profile=domain_profile,
            profile_type=profile_type,
            global_min_passwd_length=global_min_passwd_length,
            global_max_passwd_length=global_max_passwd_length,
            min_passwd_length=min_passwd_length,
            max_passwd_length=max_passwd_length,
            timezones=TIMEZONES,
            default_mta_transport=settings.default_mta_transport,
            languagemaps=iredutils.get_language_maps(),
            msg=form.get('msg', None),
        )

    @decorators.csrf_protected
    @decorators.require_global_admin
    def POST(self, profile_type, domain):
        profile_type = web.safestr(profile_type)
        domain = str(domain).lower()

        form = web.input(
            enabledService=[],
            domainAdmin=[],
            defaultList=[],
        )

        if domain != web.safestr(form.get('domainName', None)).lower():
            raise web.seeother('/profile/domain/{}/{}?msg=DOMAIN_NAME_MISMATCH'.format(profile_type, domain))

        qr = ldap_lib_domain.update(domain=domain,
                                    profile_type=profile_type,
                                    form=form,
                                    conn=None)

        if qr[0] is True:
            raise web.seeother('/profile/domain/{}/{}?msg=UPDATED'.format(profile_type, domain))
        else:
            raise web.seeother('/profile/domain/{}/{}?msg={}'.format(profile_type, domain, web.urlquote(qr[1])))


class Create:
    @decorators.require_global_admin
    def GET(self):
        form = web.input()
        domain = form_utils.get_domain_name(form=form)

        return web.render('ldap/domain/create.html',
                          preferred_language=settings.default_language,
                          languagemaps=iredutils.get_language_maps(),
                          timezones=TIMEZONES,
                          domainName=domain,
                          msg=form.get('msg'))

    @decorators.require_global_admin
    @decorators.csrf_protected
    def POST(self):
        form = web.input()
        domain = form_utils.get_domain_name(form)

        qr = ldap_lib_domain.add(form=form)

        if qr[0] is True:
            raise web.seeother('/profile/domain/general/%s?msg=CREATED' % domain)
        else:
            raise web.seeother('/create/domain?msg=%s' % web.urlquote(qr[1]))
