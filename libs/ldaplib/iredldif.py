#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import time
from web import iredconfig as cfg
from libs.ldaplib import iredutils

# Define and return LDIF structure of domain.
def ldif_maildomain(domainName, cn=None,
        mtaTransport=cfg.general.get('mtaTransport', 'dovecot'),
        enabledService=['mail'], ):
    ldif = [
            ('objectCLass',     ['mailDomain']),
            ('domainName',      [domainName.lower()]),
            ('mtaTransport',    [mtaTransport]),
            ('accountStatus',   ['active']),
            ('enabledService',  enabledService),
            ]

    if cn is not None and cn != '':
        ldif += [('cn', [cn.encode('utf-8')])]

    return ldif

def ldif_group(name):
    ldif = [
            ('objectClass',     ['organizationalUnit']),
            ('ou',              [name]),
            ]

    return ldif

def ldif_group_alias():
    ldif = [
            ('objectClass',     ['organizationalUnit']),
            ('ou',              ['Aliases']),
            ]

    return ldif

def ldif_maillist(group, domain, cn=u'Mail Group', desc=u'Mail Group',):
    group=str(group)
    domain=str(domain)

    ldif = [
            ('objectClass',     'mailList'),
            ('accountStatus',   'active'),
            ('mail',            group + '@' + domain),
            ('hasMember',       'no'),
            ]

    if cn is not None:
        ldif += [('cn', cn.encode('utf-8'))]

    if desc is not None:
        ldif += [('description', desc.encode('utf-8'))]

    return ldif

# Define and return LDIF structure of domain admin.
def ldif_mailadmin(admin, passwd, domainGlobalAdmin):
    ldif = [
            ('objectCLass',     ['mailAdmin']),
            ('mail',            [str(admin)]),
            ('userPassword',    [str(passwd)]),
            ('accountStatus',   ['active']),
            ('domainGlobalAdmin',   [str(domainGlobalAdmin)]),
            ]

    return ldif

# Define and return LDIF structure of mail user.
def ldif_mailuser(domain, username, cn, passwd, quota=cfg.general.get('default_quota')):
    DATE = time.strftime('%Y.%m.%d.%H.%M.%S')
    domain = str(domain)
    quota = int(quota) * 1024 * 1024
    username = iredutils.removeSpaceAndDot(str(username))
    mail = username.lower() + '@' + domain
    #dn = convEmailToUserDN(mail)

    maildir_domain = str(domain).lower()
    if eval(cfg.general.get('hashed_maildir', True)) is True:
        # Hashed. Length of domain name are always >= 2.
        #maildir_domain = "%s/%s/%s/" % (domain[:1], domain[:2], domain,)
        if len(username) >= 3:
            maildir_user = "%s/%s/%s/%s-%s/" % (username[:1], username[:2], username[:3], username, DATE,)
        elif len(username) == 2:
            maildir_user = "%s/%s/%s/%s-%s/" % (
                    username[:1],
                    username[:],
                    username[:] + username[-1],
                    username,
                    DATE,
                    )
        else:
            maildir_user = "%s/%s/%s/%s-%s/" % (
                    username[0],
                    username[0] * 2,
                    username[0] * 3,
                    username,
                    DATE,
                    )
        mailMessageStore = maildir_domain + maildir_user
    else:
        mailMessageStore = "%s/%s-%s/" % (domain, username, DATE,)

    homeDirectory = cfg.general.get('storage_base_directory') + '/' + mailMessageStore

    ldif = [
        ('objectCLass',         ['inetOrgPerson', 'mailUser', 'shadowAccount']),
        ('mail',                [mail]),
        ('userPassword',        [str(passwd)]),
        ('mailQuota',           [str(quota)]),
        ('sn',                  [username]),
        ('uid',                 [username]),
        ('storageBaseDirectory', [cfg.general.get('storage_base_directory')]),
        ('mailMessageStore',    [mailMessageStore]),
        ('homeDirectory',       [homeDirectory]),
        ('accountStatus',       ['active']),
        ('mtaTransport',        ['dovecot']),
        ('enabledService',      ['mail', 'smtp', 'pop3', 'imap', 'deliver', 'forward',
                                'senderbcc', 'recipientbcc', 'managesieve',
                                'displayedInGlobalAddressBook',]),
        ('memberOfGroup',       ['all@'+domain]), # Make all users belong to group 'all@domain.ltd'.
        ]

    if cn is not None and cn != '':
        ldif += [('cn', [cn.encode('utf-8')])]

    return ldif
