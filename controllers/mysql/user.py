# encoding: utf-8

# Author: Zhang Huangbin <zhb@iredmail.org>

import web
from libs import iredutils
from libs.mysql import decorators, user as userlib, domain as domainlib

cfg = web.iredconfig
session = web.config.get('_session')

class List:
    @decorators.require_login
    def GET(self, domain, cur_page=1):
        self.domain = web.safestr(domain).split('/', 1)[0]
        cur_page = int(cur_page)

        if not iredutils.isDomain(self.domain):
            return web.seeother('/domains?msg=INVALID_DOMAIN_NAME')

        if cur_page == 0:
            cur_page = 1

        userLib = userlib.User()
        result = userLib.listAccounts(domain=self.domain, cur_page=cur_page,)
        if result[0] is True:
            (total, records) = (result[1], result[2])

            return web.render(
                'mysql/user/list.html',
                cur_domain=self.domain,
                cur_page=cur_page,
                total=total,
                users=records,
                msg=web.input().get('msg', None),
            )
        else:
            return web.seeother('/domains?msg=%s' % result[1])

    @decorators.require_login
    def POST(self, domain):
        i = web.input(_unicode=False, username=[])

        self.domain = str(domain)

        if not iredutils.isDomain(self.domain):
            return web.seeother('/domains?msg=INVALID_DOMAIN_NAME')

        self.mails = [str(v)
                      for v in i.get('username', [])
                      if iredutils.isEmail(v)
                      and str(v).endswith('@'+self.domain)
                     ]

        self.action = i.get('action', None)
        msg = i.get('msg', None)

        userLib = userlib.User()

        if self.action == 'delete':
            result = userLib.delete(domain=self.domain, mails=self.mails,)
            msg = 'DELETED_SUCCESS'
        elif self.action == 'disable':
            result = userLib.enableOrDisableAccount(domain=self.domain, accounts=self.mails, active=False,)
            msg = 'DISABLED_SUCCESS'
        elif self.action == 'enable':
            result = userLib.enableOrDisableAccount(domain=self.domain, accounts=self.mails, active=True,)
            msg = 'ENABLED_SUCCESS'
        else:
            result = (False, 'INVALID_ACTION')

        if result[0] is True:
            return web.seeother('/users/%s?msg=%s' % (self.domain, msg,))
        else:
            return web.seeother('/users/%s?msg=%s' % (self.domain, result[1],))

class Profile:
    @decorators.require_login
    def GET(self, profile_type, mail):
        i = web.input()
        self.mail = str(mail).lower()
        self.cur_domain = self.mail.split('@', 1)[-1]
        self.profile_type = str(profile_type)

        if self.mail.startswith('@') and iredutils.isDomain(self.cur_domain):
            # Catchall account.
            return web.seeother('/profile/domain/catchall/%s' % (self.cur_domain))

        if not iredutils.isEmail(self.mail):
            return web.seeother('/domains?msg=INVALID_USER')

        if not iredutils.isDomain(self.cur_domain):
            return web.seeother('/domains?msg=INVALID_DOMAIN_NAME')

        userLib = userlib.User()
        qr = userLib.profile(domain=self.cur_domain, mail=self.mail)
        if qr[0] is True:
            self.profile = qr[1]
        else:
            return web.seeother('/users/%s?msg=%s' % (self.cur_domain, qr[1]))

        return web.render(
            'mysql/user/profile.html',
            cur_domain=self.cur_domain,
            mail=self.mail,
            profile_type=self.profile_type,
            profile=self.profile,
            msg=i.get('msg'),
        )

    @decorators.require_login
    def POST(self, profile_type, mail):
        i = web.input(
            enabledService=[],
            telephoneNumber=[],
        )
        self.profile_type = web.safestr(profile_type)
        self.mail = str(mail).lower()

        userLib = userlib.User()
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
    @decorators.require_login
    def GET(self, domain=None,):
        if domain is None:
            self.cur_domain = None
        else:
            self.cur_domain = str(domain)
            if not iredutils.isDomain(self.cur_domain):
                return web.seeother('/domains?msg=INVALID_DOMAIN_NAME')

        i = web.input()

        # Get all managed domains.
        domainLib = domainlib.Domain()
        result = domainLib.getAllDomains(columns=[
            'domain', 'description',
            'maxquota', 'mailboxes', 'defaultuserquota',
            'minpasswordlength', 'maxpasswordlength',
        ])

        if result[0] is True:
            allDomains=result[1]
        else:
            return web.seeother('/domains?msg=' % result[1])

        # Set first domain as current domain.
        if self.cur_domain is None:
            if len(allDomains) > 0:
                return web.seeother('/create/user/%s' % str(allDomains[0].domain))
            else:
                return web.seeother('/domains?msg=NO_DOMAIN_AVAILABLE')

        # Get domain profile.
        resultOfProfile = domainLib.profile(domain=self.cur_domain)
        if resultOfProfile[0] is True:
            self.profile = resultOfProfile[1]
        else:
            return web.seeother('/domains?msg=%s' % resultOfProfile[1])

        # Cet total number and allocated quota size of existing users under domain.
        self.numberOfExistAccounts = 0
        self.usedQuotaSize = 0

        qr = domainLib.getCountsOfExistAccountsUnderDomain(
            domain=self.cur_domain,
            accountType='user',
        )
        if qr[0] is True:
            self.numberOfExistAccounts = qr[1]
            self.usedQuotaSize = qr[2]

        return web.render(
            'mysql/user/create.html',
            cur_domain=self.cur_domain,
            allDomains=allDomains,
            profile=self.profile,
            numberOfExistAccounts=self.numberOfExistAccounts,
            usedQuotaSize=self.usedQuotaSize,
            msg=i.get('msg'),
        )

    @decorators.require_login
    def POST(self, domain):
        i = web.input()

        # Get domain name, username, cn.
        self.username = web.safestr(i.get('username', ''))
        self.cur_domain = web.safestr(i.get('domainName', ''))

        userLib = userlib.User()
        result = userLib.add(domain=self.cur_domain, data=i)
        if result[0] is True:
            return web.seeother('/profile/user/general/%s@%s?msg=CREATED_SUCCESS' % (self.username, self.cur_domain))
        else:
            return web.seeother('/create/user/%s?msg=%s' % (self.cur_domain, result[1]))
