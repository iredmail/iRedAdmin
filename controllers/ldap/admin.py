# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings
from libs import iredutils
from libs.l10n import TIMEZONES

from libs.ldaplib.core import LDAPWrap
from libs.ldaplib import decorators, ldaputils
from libs.ldaplib import admin as ldap_lib_admin
from libs.ldaplib import domain as ldap_lib_domain
from libs.ldaplib import general as ldap_lib_general

session = web.config.get('_session')


class List:
    @decorators.require_global_admin
    def GET(self, cur_page=1):
        form = web.input()
        cur_page = int(cur_page)

        if cur_page == 0:
            cur_page = 1

        qr = ldap_lib_admin.list_accounts(conn=None)

        sl = ldap_lib_general.get_paged_account_list(qr[1],
                                                     current_page=cur_page)

        if cur_page > sl['pages']:
            cur_page = sl['pages']

        return web.render('ldap/admin/list.html',
                          cur_page=cur_page,
                          total=sl['total'],
                          admins=sl['account_profiles'],
                          msg=form.get('msg', None))

    # Delete, disable, enable admin accounts.
    @decorators.require_global_admin
    @decorators.csrf_protected
    def POST(self):
        form = web.input(_unicode=False, mail=[])
        mails = form.get('mail', [])
        action = form.get('action', None)

        if action == 'delete':
            result = ldap_lib_admin.delete(mails=mails, conn=None)
            msg = 'DELETED'
        elif action == 'disable':
            result = ldap_lib_general.enable_disable_admins(mails=mails, action='disable', conn=None)
            msg = 'DISABLED'
        elif action == 'enable':
            result = ldap_lib_general.enable_disable_admins(mails=mails, action='enable', conn=None)
            msg = 'ENABLED'
        else:
            result = (False, 'INVALID_ACTION')
            msg = form.get('msg', None)

        if result[0] is True:
            raise web.seeother('/admins?msg=%s' % msg)
        else:
            raise web.seeother('/admins?msg=' + web.urlquote(result[1]))


class Create:
    @decorators.require_global_admin
    def GET(self):
        form = web.input()

        db_settings = iredutils.get_settings_from_db()
        min_passwd_length = db_settings['min_passwd_length']
        max_passwd_length = db_settings['max_passwd_length']

        password_policies = iredutils.get_password_policies(db_settings=db_settings)

        return web.render('ldap/admin/create.html',
                          languagemaps=iredutils.get_language_maps(),
                          default_language=settings.default_language,
                          min_passwd_length=min_passwd_length,
                          max_passwd_length=max_passwd_length,
                          password_policies=password_policies,
                          msg=form.get('msg'))

    @decorators.require_global_admin
    @decorators.csrf_protected
    def POST(self):
        form = web.input()
        mail = web.safestr(form.get('mail'))

        qr = ldap_lib_admin.add(form=form)

        if qr[0] is True:
            # Redirect to assign domains.
            raise web.seeother('/profile/admin/general/%s?msg=CREATED' % mail)
        else:
            raise web.seeother('/create/admin?msg=' + web.urlquote(qr[1]))


class Profile:
    @decorators.require_global_admin
    def GET(self, profile_type, mail):
        mail = web.safestr(mail).lower()
        profile_type = web.safestr(profile_type)

        if not (session.get('is_global_admin') or session.get('username') == mail):
            # Don't allow to view/update other admins' profile.
            raise web.seeother('/profile/admin/general/%s?msg=PERMISSION_DENIED' % session.get('username'))

        _wrap = LDAPWrap()
        conn = _wrap.conn

        # Get admin profile.
        qr = ldap_lib_admin.get_profile(mail=mail, conn=conn)
        if qr[0]:
            admin_profile = qr[1]['ldif']
            account_settings = ldaputils.get_account_setting_from_profile(admin_profile)
            _qr = ldap_lib_general.get_admin_account_setting(mail=mail,
                                                             profile=admin_profile,
                                                             conn=conn)
            if _qr[0]:
                account_settings = _qr[1]
        else:
            raise web.seeother('/admins?msg=' + qr[1])

        form = web.input()

        if profile_type in ['general', 'password']:
            # Get all domains.
            qr_all_domains = ldap_lib_domain.list_accounts(attributes=['domainName', 'cn'], conn=conn)
            if qr_all_domains[0] is True:
                all_domains = qr_all_domains[1]
            else:
                return qr_all_domains

            # Get domains under control.
            qr_managed_domains = ldap_lib_admin.get_managed_domains(admin=mail,
                                                                    attributes=['domainName'],
                                                                    domain_name_only=True,
                                                                    conn=conn)

            if qr_managed_domains[0] is True:
                managed_domains = qr_managed_domains[1]
            else:
                return qr_managed_domains

            return web.render(
                'ldap/admin/profile.html',
                mail=mail,
                profile_type=profile_type,
                admin_profile=admin_profile,
                account_settings=account_settings,
                languagemaps=iredutils.get_language_maps(),
                allDomains=all_domains,
                managedDomains=managed_domains,
                min_passwd_length=settings.min_passwd_length,
                max_passwd_length=settings.max_passwd_length,
                store_password_in_plain_text=settings.STORE_PASSWORD_IN_PLAIN_TEXT,
                password_policies=iredutils.get_password_policies(),
                timezones=TIMEZONES,
                msg=form.get('msg', None),
            )

    @decorators.csrf_protected
    @decorators.require_global_admin
    def POST(self, profile_type, mail):
        mail = web.safestr(mail).lower()
        form = web.input(domainName=[])

        if (not session.get('is_global_admin')) and (session.get('username') != mail):
            # Don't allow to view/update other admin's profile.
            raise web.seeother('/profile/admin/general/%s?msg=PERMISSION_DENIED' % session.get('username'))

        qr = ldap_lib_admin.update_profile(form=form,
                                           mail=mail,
                                           profile_type=profile_type)

        if qr[0]:
            raise web.seeother('/profile/admin/general/%s?msg=UPDATED' % (mail))
        else:
            raise web.seeother('/profile/admin/general/{}?msg={}'.format(mail, qr[1]))
