#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import sys
import web
from web import render
from web import iredconfig as cfg
from controllers.ldap import base
from controllers.ldap.core import dbinit
from libs.ldaplib import domain, user, iredldif, iredutils

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

        allDomains = domainLib.list()

        if domain == '' or domain is None:
            return render.users(allDomains=allDomains)

        users = userLib.list(domain=domain)
        if users is not False:
            return render.users(
                    users=users, cur_domain=domain,
                    allDomains=allDomains,
                    msg=None,
                    )
        else:
            web.seeother('/domains?msg=NO_SUCH_DOMAIN')

    @base.protected
    def POST(self, domain):
        i = web.input(_unicode=False, mail=[])
        mails = i.mail
        result = userLib.delete(mails=mails)
        web.seeother('/users/' + str(domain))

class profile(dbinit):
    @base.protected
    def GET(self, email):
        #i = web.input()
        email = web.safestr(email)

        if len(email.split('@', 1)) == 2:
            domain = email.split('@', 1)[1]
            userdn = iredutils.convEmailToUserDN(email)

            if userdn:
                profile = userLib.profile(dn=userdn)
                return render.user_profile(user_profile=profile)
            else:
                web.seeother('/domains')
        else:
            web.seeother('/domains')

class create(dbinit):
    @base.protected
    def GET(self, domainName=None):
        if domainName is None:
            domainName = ''
        else:
            domainName = web.safestr(domainName)

        default_quota = cfg.general.get('default_quota', '1024')
        return render.user_create(
                domainName=domainName,
                allDomains=domainLib.list(),
                default_quota=session.get('default_quota'),
                )

    @base.protected
    def POST(self):
        i = web.input()

        # Get domain name, username, cn.
        domain = i.get('domainName', None)
        username = i.get('username', None)

        if domain is None or username is None:
            return render.user_create(
                    domainName=domain,
                    allDomains=domainLib.list(),
                    )

        cn = i.get('cn', None)
        quota = i.get('quota', session.get('default_quota'))

        # Check password.
        newpw = web.safestr(i.get('newpw'))
        confirmpw = web.safestr(i.get('confirmpw'))
        if len(newpw) > 0 and len(confirmpw) > 0 and newpw == confirmpw:
            passwd = iredutils.generatePasswd(newpw, pwscheme=cfg.general.get('default_pw_scheme', 'SSHA'))
        else:
            return render.user_create(
                    domainName=domain,
                    allDomains=domainLib.list(),
                    username=username,
                    cn=cn,
                    msg='PW_ERROR',
                    )

        ldif = iredldif.ldif_mailuser(
                domain=web.safestr(domain),
                username=web.safestr(username),
                cn=cn,
                passwd=passwd,
                quota=quota,
                )

        dn = iredutils.convEmailToUserDN(username + '@' + domain)
        result = userLib.add(dn, ldif)
        if result is True:
            web.seeother('/users/' + domain)
        elif result == 'ALREADY_EXISTS':
            web.seeother('/users/' + domain + '?msg=ALREADY_EXISTS')
        else:
            web.seeother('/users/' + domain)

class delete(dbinit):
    @base.protected
    def POST(self):
        i = web.input(mail=[])
        domain = i.get('domain', None)
        if domain is None:
            web.seeother('/users?msg=NO_DOMAIN')

        mails = i.get('mail', [])
        for mail in mails:
            dn = ldap.filter.escape_filter_chars(iredutils.convEmailToUserDN(mail))
        print >> sys.stderr, i 
        web.seeother('/users/' + web.safestr(domain))
