#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import types, sys
import web
from web import render
from web import iredconfig as cfg
from controllers.ldap import base
from controllers.ldap.basic import dbinit
from libs.ldaplib import domain, user, attrs, iredldif, ldaputils

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
        self.mails = i.get('mail', [])
        result = userLib.delete(domain=self.domain, mails=self.mails)
        web.seeother('/users/%s' % self.domain)

class profile(dbinit):
    @base.protected
    def GET(self, profile_type, mail):
        i = web.input(enabledService=[],telephoneNumber=[],mailForwardingAddress=[],)
        self.mail = web.safestr(mail)
        self.profile_type = web.safestr(profile_type)

        if len(self.mail.split('@')) != 2:
            web.seeother('/domains?msg=INVALID_USER')

        self.domain = self.mail.split('@')[1]
        if self.profile_type not in attrs.USER_PROFILE_TYPE:
            web.seeother('/users/%s?msg=INVALID_PROFILE_TYPE&profile_type=%s' % (self.domain, self.profile_type) )

        self.user_profile = userLib.profile(mail=self.mail)
        if self.user_profile[0] is True:
            return render.user_profile(
                    profile_type=self.profile_type,
                    mail=self.mail,
                    user_profile=self.user_profile[1],
                    min_passwd_length=cfg.general.get('min_passwd_length'),
                    max_passwd_length=cfg.general.get('max_passwd_length'),
                    msg=i.get('msg', None)
                    )
        else:
            web.seeother('/users/%s?msg=%s' % (self.domain, self.user_profile[1]))

    @base.protected
    def POST(self, profile_type, mail):
        i = web.input(enabledService=[],telephoneNumber=[],mailForwardingAddress=[],)
        self.profile_type = web.safestr(profile_type)
        self.mail = web.safestr(mail)

        result = userLib.update(
                profile_type=self.profile_type,
                mail=self.mail,
                data=i,
                )
        if result[0] is True:
            web.seeother('/profile/user/%s/%s?msg=UPDATED_SUCCESS' % (self.profile_type, self.mail))
        else:
            web.seeother('/profile/user/%s/%s?msg=%s' % (self.profile_type, self.mail, result[1]))

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

        result = userLib.add(domain=self.domain, data=i)
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
