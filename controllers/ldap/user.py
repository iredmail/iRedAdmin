#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import types, sys
import web
from web import render
from web import iredconfig as cfg
from controllers.ldap import base
from controllers.ldap.basic import dbinit
from libs.ldaplib import domain, user, iredldif, ldaputils

session = web.config.get('_session')

domainLib = domain.Domain()
userLib = user.User()

#
# User related.
#
class list(dbinit):
    def __del__(self):
        pass

    @base.protected
    def GET(self, domain=''):
        domain = web.safestr(domain.split('/', 1)[0])
        allDomains = domainLib.list(attrs=['domainName'])

        if domain == '' or domain is None:
            #return render.users(allDomains=allDomains)

            # List users if only one domain available.
            if isinstance(allDomains, types.ListType) is True and len(allDomains) == 1:
                cur_domain = str(allDomains[0][1]['domainName'][0])
                result = userLib.list(domain=cur_domain)
                if result[0] is True:
                    web.seeother('/users/' + cur_domain)
                else:
                    web.seeother('/domains?msg=%s' % result[1] )
            elif isinstance(allDomains, types.ListType) is True and len(allDomains) == 0:
                return render.users(msg='NO_DOMAIN_AVAILABLE')
            elif isinstance(allDomains, types.ListType) is True and len(allDomains) > 1:
                return render.users(allDomains=allDomains)
            else:
                web.seeother('/domains?msg=NO_SUCH_DOMAIN')
        else:
            result = userLib.list(domain=domain)
            if result[0] is True:
                return render.users(
                        users=result[1], cur_domain=domain,
                        allDomains=allDomains,
                        msg=None,
                        )
            else:
                web.seeother('/domains?msg=%s' % result[1])

    @base.protected
    def POST(self, domain):
        i = web.input(_unicode=False, mail=[])
        self.domain = web.safestr(domain)
        mails = i.mail
        result = userLib.delete(domain=self.domain, mails=mails)
        web.seeother('/users/%s' % self.domain)

class profile(dbinit):
    @base.protected
    def GET(self, profile_type, mail):
        i = web.input(enabledService=[], telephoneNumber=[],)
        self.mail = web.safestr(mail)
        self.profile_type = web.safestr(profile_type)

        if len(self.mail.split('@', 1)) == 2 and \
                self.profile_type in ['general', 'shadow', 'groups', 'services', 'forwarding', 'bcc', 'password', 'advanced',]:
            self.domain = self.mail.split('@', 1)[1]

            self.profile = userLib.profile(mail=self.mail)
            if self.profile:
                return render.user_profile(
                        profile_type=self.profile_type,
                        mail=self.mail,
                        user_profile=self.profile,
                        min_passwd_length=cfg.general.get('min_passwd_length'),
                        max_passwd_length=cfg.general.get('max_passwd_length'),
                        msg=i.get('msg', None)
                        )
            else:
                web.seeother('/users/' + '?msg=PERMISSION_DENIED')
        else:
            web.seeother('/domains?msg=INVALID_REQUEST')

    @base.protected
    def POST(self, profile_type, mail):
        i = web.input(enabledService=[], telephoneNumber=[],)
        self.profile_type = web.safestr(profile_type)
        self.mail = web.safestr(mail)

        self.result = userLib.update(
                profile_type=self.profile_type,
                mail=self.mail,
                data=i,
                )
        if self.result is True:
            web.seeother('/profile/user/%s/%s?msg=UPDATED_SUCCESS' % (self.profile_type, self.mail))
        elif self.result[0] is False:
            web.seeother('/profile/user/%s/%s?msg=%s' % (self.profile_type, self.mail, self.result[1]))

class create(dbinit):
    @base.protected
    def GET(self, domainName=None):
        if domainName is None:
            self.domain = ''
        else:
            self.domain = web.safestr(domainName)

        return render.user_create(
                domain=self.domain,
                allDomains=domainLib.list(),
                default_quota=domainLib.getDomainDefaultUserQuota(self.domain),
                min_passwd_length=cfg.general.get('min_passwd_length'),
                max_passwd_length=cfg.general.get('max_passwd_length'),
                )

    @base.protected
    def POST(self):
        i = web.input()

        # Get domain name, username, cn.
        self.domain = web.safestr(i.get('domainName'))
        self.username = web.safestr(i.get('username'))

        result = userLib.add(data=i)
        if result[0] is True:
            web.seeother('/profile/user/general/%s?msg=SUCCESS' % (self.username + '@' + self.domain))
        else:
            self.cn = i.get('cn', '')
            self.quota = i.get('quota', domainLib.getDomainDefaultUserQuota(self.domain))
            return render.user_create(
                    domain=self.domain,
                    username=self.username,
                    cn=self.cn,
                    quota=self.quota,
                    allDomains=domainLib.list(),
                    default_quota=domainLib.getDomainDefaultUserQuota(self.domain),
                    min_passwd_length=cfg.general.get('min_passwd_length'),
                    max_passwd_length=cfg.general.get('max_passwd_length'),
                    msg=result[1],
                    )
