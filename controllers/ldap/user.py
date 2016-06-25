# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings
from libs import iredutils, form_utils
from libs.languages import get_language_maps
from libs.ldaplib import decorators, domain as domainlib, user, ldaputils, connUtils

session = web.config.get('_session')

#
# User related.
#
class List:
    def __del__(self):
        pass

    @decorators.require_login
    def GET(self, domain='', cur_page=1):
        domain = web.safestr(domain).split('/', 1)[0]
        cur_page = int(cur_page)

        if not iredutils.is_domain(domain):
            raise web.seeother('/domains?msg=INVALID_DOMAIN_NAME')

        if cur_page == 0:
            cur_page = 1

        i = web.input()

        domainLib = domainlib.Domain()
        result = domainLib.listAccounts(attrs=['domainName', 'accountStatus', ])
        if result[0] is True:
            allDomains = result[1]
        else:
            return result

        userLib = user.User()
        result = userLib.listAccounts(domain=domain)
        if result[0] is True:
            connutils = connUtils.Utils()
            sl = connutils.getSizelimitFromAccountLists(
                result[1],
                curPage=cur_page,
                sizelimit=settings.PAGE_SIZE_LIMIT,
                accountType='user',
                domain=domain,
            )

            accountList = sl.get('accountList', [])

            if cur_page > sl.get('totalPages'):
                cur_page = sl.get('totalPages')

            return web.render(
                'ldap/user/list.html',
                cur_page=cur_page,
                total=sl.get('totalAccounts'),
                users=accountList,
                cur_domain=domain,
                allDomains=allDomains,
                accountUsedQuota={},
                msg=i.get('msg'),
            )
        else:
            raise web.seeother('/domains?msg=%s' % web.urlquote(result[1]))

    # Delete users.
    @decorators.csrf_protected
    @decorators.require_login
    def POST(self, domain):
        i = web.input(_unicode=False, mail=[])
        self.domain = web.safestr(domain)
        self.mails = i.get('mail', [])
        action = i.get('action', None)

        userLib = user.User()

        if action == 'delete':
            keep_mailbox_days = form_utils.get_single_value(form=i,
                                                            input_name='keep_mailbox_days',
                                                            default_value=0,
                                                            is_integer=True)
            result = userLib.delete(domain=self.domain, mails=self.mails, keep_mailbox_days=keep_mailbox_days)
            msg = 'DELETED'
        elif action == 'disable':
            result = userLib.enableOrDisableAccount(domain=self.domain, mails=self.mails, action='disable',)
            msg = 'DISABLED'
        elif action == 'enable':
            result = userLib.enableOrDisableAccount(domain=self.domain, mails=self.mails, action='enable',)
            msg = 'ENABLED'
        else:
            result = (False, 'INVALID_ACTION')
            msg = i.get('msg', None)

        if result[0] is True:
            cur_page = i.get('cur_page', '1')
            raise web.seeother('/users/%s/page/%s?msg=%s' % (self.domain, str(cur_page), msg, ))
        else:
            raise web.seeother('/users/%s?msg=%s' % (self.domain, web.urlquote(result[1])))


class Profile:
    @decorators.require_login
    def GET(self, profile_type, mail):
        i = web.input(enabledService=[], telephoneNumber=[], )
        self.mail = web.safestr(mail)
        self.cur_domain = self.mail.split('@', 1)[-1]
        self.profile_type = web.safestr(profile_type)

        if self.mail.startswith('@') and iredutils.is_domain(self.cur_domain):
            # Catchall account.
            raise web.seeother('/profile/domain/catchall/%s' % self.cur_domain)

        if not iredutils.is_email(self.mail):
            raise web.seeother('/domains?msg=INVALID_USER')

        domainAccountSetting = {}

        userLib = user.User()
        result = userLib.profile(domain=self.cur_domain, mail=self.mail)
        if result[0] is False:
            raise web.seeother('/users/%s?msg=%s' % (self.cur_domain, web.urlquote(result[1])))

        if self.profile_type == 'password':
            # Get accountSetting of current domain.
            domainLib = domainlib.Domain()
            result_setting = domainLib.getDomainAccountSetting(domain=self.cur_domain)
            if result_setting[0] is True:
                domainAccountSetting = result_setting[1]

        minPasswordLength = domainAccountSetting.get('minPasswordLength', '0')
        maxPasswordLength = domainAccountSetting.get('maxPasswordLength', '0')

        return web.render(
            'ldap/user/profile.html',
            profile_type=self.profile_type,
            mail=self.mail,
            user_profile=result[1],
            defaultStorageBaseDirectory=settings.storage_base_directory,
            minPasswordLength=minPasswordLength,
            maxPasswordLength=maxPasswordLength,
            domainAccountSetting=domainAccountSetting,
            languagemaps=get_language_maps(),
            msg=i.get('msg', None),
        )

    @decorators.csrf_protected
    @decorators.require_login
    def POST(self, profile_type, mail):
        i = web.input(
            enabledService=[],
            mailForwardingAddress=[],
            telephoneNumber=[],
            memberOfGroup=[],
        )
        self.profile_type = web.safestr(profile_type)
        self.mail = web.safestr(mail)

        userLib = user.User()
        result = userLib.update(
            profile_type=self.profile_type,
            mail=self.mail,
            data=i,
        )

        if result[0] is True:
            raise web.seeother('/profile/user/%s/%s?msg=UPDATED' % (self.profile_type, self.mail))
        else:
            raise web.seeother('/profile/user/%s/%s?msg=%s' % (self.profile_type, self.mail, web.urlquote(result[1])))


class Create:
    @decorators.require_login
    def GET(self, domainName=None):
        i = web.input()

        if domainName is None:
            self.cur_domain = ''
        else:
            self.cur_domain = web.safestr(domainName)

        domainLib = domainlib.Domain()
        result = domainLib.listAccounts(attrs=['domainName', 'accountSetting', 'domainCurrentQuotaSize', ])
        if result[0] is True:
            allDomains = result[1]

            if len(allDomains) == 0:
                raise web.seeother('/domains?msg=NO_DOMAIN_AVAILABLE')
            else:
                # Redirect to create new user under first domain, so that we
                # can get per-domain account settings, such as number of
                # account limit, password length control, etc.
                if self.cur_domain == '':
                    raise web.seeother('/create/user/' + str(allDomains[0][1]['domainName'][0]))

            # Get accountSetting of current domain.
            allAccountSettings = ldaputils.getAccountSettingFromLdapQueryResult(allDomains, key='domainName')
            domainAccountSetting = allAccountSettings.get(self.cur_domain, {})
            defaultUserQuota = domainLib.getDomainDefaultUserQuota(self.cur_domain, domainAccountSetting)
        else:
            raise web.seeother('/domains?msg=' % web.urlquote(result[1]))

        # Get number of account limit.
        connutils = connUtils.Utils()
        result = connutils.getNumberOfCurrentAccountsUnderDomain(self.cur_domain, accountType='user', )
        if result[0] is True:
            numberOfCurrentAccounts = result[1]
        else:
            numberOfCurrentAccounts = 0

        # Get current domain quota size.
        result = connutils.getDomainCurrentQuotaSizeFromLDAP(domain=self.cur_domain)
        if result[0] is True:
            domainCurrentQuotaSize = result[1]
        else:
            # -1 means temporary error. Don't allow to create new user.
            domainCurrentQuotaSize = -1

        return web.render('ldap/user/create.html',
                          cur_domain=self.cur_domain,
                          allDomains=allDomains,
                          defaultUserQuota=defaultUserQuota,
                          domainAccountSetting=domainAccountSetting,
                          numberOfCurrentAccounts=numberOfCurrentAccounts,
                          domainCurrentQuotaSize=domainCurrentQuotaSize,
                          msg=i.get('msg'))

    @decorators.csrf_protected
    @decorators.require_login
    def POST(self):
        i = web.input()

        # Get domain name, username, cn.
        self.cur_domain = web.safestr(i.get('domainName'))
        self.username = web.safestr(i.get('username'))

        userLib = user.User()
        result = userLib.add(domain=self.cur_domain, data=i)
        if result[0] is True:
            raise web.seeother('/profile/user/general/%s?msg=CREATED' % (self.username + '@' + self.cur_domain))
        else:
            raise web.seeother('/create/user/%s?msg=%s' % (self.cur_domain, web.urlquote(result[1])))
