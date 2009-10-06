#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

#---------------------------------------------------------------------
# This file is part of iRedAdmin-OSE, which is official web-based admin
# panel (Open Source Edition) for iRedMail.
#
# iRedMail is an open source mail server solution for Red Hat(R)
# Enterprise Linux, CentOS, Debian and Ubuntu.
#
# iRedAdmin-OSE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# iRedAdmin-OSE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with iRedAdmin-OSE.  If not, see <http://www.gnu.org/licenses/>.
#---------------------------------------------------------------------

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
        i = web.input()
        result = domainLib.list(attrs=['domainName'])
        if result[0] is True:
            allDomains = result[1]
        else:
            return result

        if domain == '' or domain is None:
            # List users if only one domain available.
            if isinstance(allDomains, types.ListType) is True and len(allDomains) == 1:
                cur_domain = str(allDomains[0][1]['domainName'][0])
                result = userLib.list(domain=cur_domain)
                if result[0] is True:
                    web.seeother('/users/' + cur_domain)
                else:
                    web.seeother('/domains?' + result[1] )
            elif isinstance(allDomains, types.ListType) is True and len(allDomains) == 0:
                return render.users(msg='NO_DOMAIN_AVAILABLE')
            elif isinstance(allDomains, types.ListType) is True and len(allDomains) > 1:
                return render.users(allDomains=allDomains, msg=i.get('msg'),)
            else:
                web.seeother('/domains?msg=NO_SUCH_DOMAIN')
        else:
            result = userLib.list(domain=domain)
            if result[0] is True:
                return render.users(
                        users=result[1],
                        cur_domain=domain,
                        allDomains=allDomains,
                        msg=i.get('msg'),
                        )
            else:
                web.seeother('/domains?' + result[1])

    @base.protected
    def POST(self, domain):
        i = web.input(_unicode=False, mail=[])
        self.domain = web.safestr(domain)
        self.mails = i.get('mail', [])
        if i.has_key('delete'):
            result = userLib.delete(domain=self.domain, mails=self.mails,)
            msg = 'DELETED_SUCCESS'
        elif i.has_key('disable'):
            result = userLib.enableOrDisableAccount(domain=self.domain, mails=self.mails, value='disabled',)
            msg = 'DISABLED_SUCCESS'
        elif i.has_key('enable'):
            result = userLib.enableOrDisableAccount(domain=self.domain, mails=self.mails, value='active',)
            msg = 'ENABLED_SUCCESS'
        else:
            msg = i.get('msg', None)

        if result[0] is True:
            web.seeother('/users/%s?msg=%s' % (self.domain, msg))
        else:
            web.seeother('/users/%s?' % (self.domain) + result[1])

class profile(dbinit):
    @base.protected
    def GET(self, profile_type, mail):
        i = web.input(
                enabledService=[],
                telephoneNumber=[],
                mailForwardingAddress=[],
                memberOfGroup=[],
                )
        self.mail = web.safestr(mail)
        self.profile_type = web.safestr(profile_type)

        if len(self.mail.split('@')) != 2:
            web.seeother('/domains?msg=INVALID_USER')

        self.domain = self.mail.split('@')[1]
        if self.profile_type not in attrs.USER_PROFILE_TYPE:
            web.seeother('/users/%s?msg=INVALID_PROFILE_TYPE&profile_type=%s' % (self.domain, self.profile_type) )

        result = userLib.profile(domain=self.domain, mail=self.mail)
        if result[0] is True:
            return render.user_profile(
                    profile_type=self.profile_type,
                    mail=self.mail,
                    user_profile=result[1],
                    min_passwd_length=cfg.general.get('min_passwd_length'),
                    max_passwd_length=cfg.general.get('max_passwd_length'),
                    msg=i.get('msg', None)
                    )
        else:
            web.seeother('/users/%s?' % (self.domain) + result[1])

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
            web.seeother('/profile/user/%s/%s?msg=PROFILE_UPDATED_SUCCESS' % (self.profile_type, self.mail))
        else:
            web.seeother('/profile/user/%s/%s?' % (self.profile_type, self.mail) + result[1])

class create(dbinit):
    @base.protected
    def GET(self, domainName=None):
        if domainName is None:
            self.domain = ''
        else:
            self.domain = web.safestr(domainName)

        result = domainLib.list()
        if result[0] is True:
            allDomains = result[1]
        else:
            return result
        return render.user_create(
                domain=self.domain,
                allDomains=allDomains,
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
            web.seeother('/profile/user/general/%s?msg=CREATED_SUCCESS' % (self.username + '@' + self.domain))
        else:
            self.cn = i.get('cn', '')
            self.quota = i.get('quota', domainLib.getDomainDefaultUserQuota(self.domain))

            r = domainLib.list()
            if r[0] is True:
                allDomains = r[1]
            else:
                return r

            return render.user_create(
                    domain=self.domain,
                    username=self.username,
                    cn=self.cn,
                    quota=self.quota,
                    allDomains=allDomains,
                    default_quota=domainLib.getDomainDefaultUserQuota(self.domain),
                    min_passwd_length=cfg.general.get('min_passwd_length'),
                    max_passwd_length=cfg.general.get('max_passwd_length'),
                    msg=result[1],
                    )
