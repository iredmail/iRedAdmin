# Author: Zhang Huangbin <zhb@iredmail.org>

import sys
import web
from controllers import base
from libs import iredutils
from libs.ldaplib import domain as domainlib, user, ldaputils, connUtils

cfg = web.iredconfig
session = web.config.get('_session')


#
# User related.
#


class List:
    def __del__(self):
        pass

    @base.require_login
    def GET(self, domain='', cur_page=1):
        domain = web.safestr(domain).split('/', 1)[0]
        cur_page = int(cur_page)

        if not iredutils.isDomain(domain):
            return web.seeother('/domains?msg=INVALID_DOMAIN_NAME')

        if cur_page == 0:
            cur_page = 1

        i = web.input()

        domainLib = domainlib.Domain()
        result = domainLib.listAccounts(attrs=['domainName', 'accountStatus',])
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
                sizelimit=session['pageSizeLimit'],
                accountType='user',
                domain=domain,
            )

            accountList = sl.get('accountList', [])

            ############################
            # Get real-time used quota.
            #
            # Pre-defined dict of account used quota.
            accountUsedQuota = {}

            if session.get('enableShowUsedQuota', False) is True:
                # Get email address list.
                accountEmailLists = []
                for tmpuser in accountList:
                    accountEmailLists += tmpuser[1].get('mail', [])

                if len(accountEmailLists) > 0:
                    try:
                        accountUsedQuota = iredutils.getAccountUsedQuota(accountEmailLists)
                    except Exception, e:
                        pass
            #
            # END. Get real-time used quota.
            ################################

            if cur_page > sl.get('totalPages'):
                cur_page = sl.get('totalPages')

            # Show login date.
            if cfg.general.get('show_login_date', 'False').lower() in ['true',]:
                showLoginDate = True
            else:
                showLoginDate = False

            return web.render(
                'ldap/user/list.html',
                cur_page=cur_page,
                total=sl.get('totalAccounts'),
                users=accountList,
                cur_domain=domain,
                allDomains=allDomains,
                showLoginDate=showLoginDate,
                accountUsedQuota=accountUsedQuota,
                msg=i.get('msg'),
            )
        else:
            return web.seeother('/domains?msg=%s' % result[1])

    # Delete users.
    @base.require_login
    def POST(self, domain):
        i = web.input(_unicode=False, mail=[])
        self.domain = web.safestr(domain)
        self.mails = i.get('mail', [])
        self.action = i.get('action', None)

        userLib = user.User()

        if self.action == 'delete':
            result = userLib.delete(domain=self.domain, mails=self.mails,)
            msg = 'DELETED_SUCCESS'
        elif self.action == 'disable':
            result = userLib.enableOrDisableAccount(domain=self.domain, mails=self.mails, action='disable',)
            msg = 'DISABLED_SUCCESS'
        elif self.action == 'enable':
            result = userLib.enableOrDisableAccount(domain=self.domain, mails=self.mails, action='enable',)
            msg = 'ENABLED_SUCCESS'
        else:
            result = (False, 'INVALID_ACTION')
            msg = i.get('msg', None)

        if result[0] is True:
            cur_page = i.get('cur_page', '1')
            return web.seeother('/users/%s/page/%s?msg=%s' % (self.domain, str(cur_page), msg, ))
        else:
            return web.seeother('/users/%s?msg=%s' % (self.domain, result[1]))


class Profile:
    @base.require_login
    def GET(self, profile_type, mail):
        i = web.input(enabledService=[], telephoneNumber=[], )
        self.mail = web.safestr(mail)
        self.cur_domain = self.mail.split('@', 1)[-1]
        self.profile_type = web.safestr(profile_type)

        if self.mail.startswith('@') and iredutils.isDomain(self.cur_domain):
            # Catchall account.
            return web.seeother('/profile/domain/catchall/%s' % (self.cur_domain))

        if not iredutils.isEmail(self.mail):
            return web.seeother('/domains?msg=INVALID_USER')

        userLib = user.User()
        result = userLib.profile(domain=self.cur_domain, mail=self.mail)
        if result[0] is True:
            if self.profile_type == 'general':
                # Get account used quota.
                if session.get('enableShowUsedQuota') is True:
                    try:
                        accountUsedQuota = iredutils.getAccountUsedQuota([self.mail])
                    except Exception, e:
                        pass

            elif self.profile_type == 'password':
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
                minPasswordLength=minPasswordLength,
                maxPasswordLength=maxPasswordLength,
                msg=i.get('msg', None),
            )
        else:
            return web.seeother('/users/%s?msg=%s' % (self.cur_domain, result[1]))

    @base.require_login
    def POST(self, profile_type, mail):
        i = web.input(
            enabledService=[],
            telephoneNumber=[],
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
            return web.seeother('/profile/user/%s/%s?msg=PROFILE_UPDATED_SUCCESS' % (self.profile_type, self.mail))
        else:
            return web.seeother('/profile/user/%s/%s?msg=%s' % (self.profile_type, self.mail, result[1]))


class Create:
    @base.require_login
    def GET(self, domainName=None):
        i = web.input()

        if domainName is None:
            self.cur_domain = ''
        else:
            self.cur_domain = web.safestr(domainName)

        domainLib = domainlib.Domain()
        result = domainLib.listAccounts(attrs=['domainName', 'accountSetting', 'domainCurrentQuotaSize',])
        if result[0] is True:
            allDomains = result[1]

            if len(allDomains) == 0:
                return web.seeother('/domains?msg=NO_DOMAIN_AVAILABLE')
            else:
                # Redirect to create new user under first domain, so that we
                # can get per-domain account settings, such as number of
                # account limit, password length control, etc.
                if self.cur_domain == '':
                    return web.seeother('/create/user/' + str(allDomains[0][1]['domainName'][0]))

            # Get accountSetting of current domain.
            allAccountSettings = ldaputils.getAccountSettingFromLdapQueryResult(allDomains, key='domainName')
            domainAccountSetting = allAccountSettings.get(self.cur_domain, {})
            defaultUserQuota = domainLib.getDomainDefaultUserQuota(self.cur_domain, domainAccountSetting)
        else:
            return web.seeother('/domains?msg=' % result[1])

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
                          msg=i.get('msg'),
                         )

    @base.require_login
    def POST(self):
        i = web.input()

        # Get domain name, username, cn.
        self.cur_domain = web.safestr(i.get('domainName'))
        self.username = web.safestr(i.get('username'))

        userLib = user.User()
        result = userLib.add(domain=self.cur_domain, data=i)
        if result[0] is True:
            return web.seeother('/profile/user/general/%s?msg=CREATED_SUCCESS' % (self.username + '@' + self.cur_domain))
        else:
            return web.seeother('/create/user/%s?msg=%s' % (self.cur_domain, result[1]))
