# Author: Zhang Huangbin <zhb@iredmail.org>

import sys
import os
import types
from base64 import b64encode
import web
import ldap
from ldap.filter import escape_filter_chars
from libs import iredutils
from libs.ldaplib import attrs

cfg = web.iredconfig
session = web.config.get('_session')

basedn = cfg.ldap['basedn']
domainadmin_dn = cfg.ldap['domainadmin_dn']

#
# ---- Convert value to DN ----
#
def convKeywordToDN(keyword, accountType='user'):
    keyword = web.safestr(keyword).strip().replace(' ', '')
    accountType == web.safestr(accountType)

    # No matter what account type is, try to get a domain name.
    domain = keyword.split('@')[-1]

    # Validate account type.
    if accountType not in attrs.ACCOUNT_TYPES_ALL:
        return (False, 'INVALID_ACCOUNT_TYPE')

    # Validate keyword.
    # Keyword is email address.
    if accountType in attrs.ACCOUNT_TYPES_EMAIL and \
       not iredutils.isEmail(keyword):
        return (False, 'INVALID_MAIL')

    # Keyword is domain name.
    if accountType in attrs.ACCOUNT_TYPES_DOMAIN and \
       not iredutils.isDomain(keyword):
        return (False, 'INVALID_DOMAIN_NAME')

    # Convert keyword to DN.
    if accountType == 'user':
        dn = '%s=%s,%s%s=%s,%s' % (
            attrs.RDN_USER, keyword,
            attrs.DN_BETWEEN_USER_AND_DOMAIN,
            attrs.RDN_DOMAIN, domain,
            basedn,
        )
    elif accountType == 'maillist':
        dn = '%s=%s,%s%s=%s,%s' % (
            attrs.RDN_MAILLIST, keyword,
            attrs.DN_BETWEEN_MAILLIST_AND_DOMAIN,
            attrs.RDN_DOMAIN, domain,
            basedn,
        )
    elif accountType == 'maillistExternal':
        dn = '%s=%s,%s%s=%s,%s' % (
            attrs.RDN_MAILLIST_EXTERNAL, keyword,
            attrs.DN_BETWEEN_MAILLIST_EXTERNAL_AND_DOMAIN,
            attrs.RDN_DOMAIN, domain,
            basedn,
        )
    elif accountType == 'alias':
        dn = '%s=%s,%s%s=%s,%s' % (
            attrs.RDN_ALIAS, keyword,
            attrs.DN_BETWEEN_ALIAS_AND_DOMAIN,
            attrs.RDN_DOMAIN, domain,
            basedn,
        )
    elif accountType == 'admin':
        dn = '%s=%s,%s' % (
            attrs.RDN_ADMIN, keyword,
            domainadmin_dn,
        )
    elif accountType == 'catchall':
        dn = '%s=@%s,%s%s=%s,%s' % (
            attrs.RDN_CATCHALL, domain,
            attrs.DN_BETWEEN_CATCHALL_AND_DOMAIN,
            attrs.RDN_DOMAIN, domain,
            basedn,
        )
    elif accountType == 'domain':
        dn = '%s=%s,%s' % (
            attrs.RDN_DOMAIN, keyword,
            basedn,
        )

    return escape_filter_chars(dn)
# ---- End Convert value to DN ----

def removeSpace(s):
    """Remove all whitespace."""
    return str(s).strip().replace(' ', '')

# Generate attribute list & values from form data.
def getModAttrs(accountType, data):
    accountType = web.safestr(accountType)
    domainName = web.safestr(data.get('domainName', None))
    if domainName == 'None' or domainName == '':
        return False

    # Init attrs & values.
    mod_attrs = []

    cn = data.get('cn', None)
    if cn is not None and cn != '':
        mod_attrs += [ ( ldap.MOD_REPLACE, 'cn', cn.encode('utf-8') ) ]

    # Get accountStatus.
    accountStatus = web.safestr(data.get('accountStatus', 'active'))
    if accountStatus not in attrs.ACCOUNT_STATUSES:
        accountStatus = 'active'
    mod_attrs += [ (ldap.MOD_REPLACE, 'accountStatus', accountStatus) ]

    if session.get('domainGlobalAdmin') is True:
        # Convert to string, they don't contain non-ascii characters.

        # Get enabledService.
        if 'enabledService' in data.keys():
            enabledService = [ web.safestr(v)
                    for v in data.get('enabledService')
                    if v in attrs.DOMAIN_ENABLED_SERVICE
                    ]

            if len(enabledService) == 0:
                # Delete all values.
                mod_attrs += [ (ldap.MOD_DELETE, 'enabledService', None), ]
            else:
                # Replace all exist values by new values.
                mod_attrs += [ (ldap.MOD_REPLACE, 'enabledService', enabledService), ]

        # Get domain attributes.
        if accountType == 'domain':
            dn = convKeywordToDN(domainName, accountType='domain')

            # Get domainBackupMX.
            domainBackupMX = web.safestr(data.get('domainBackupMX', 'no'))
            if domainBackupMX not in attrs.VALUES_DOMAIN_BACKUPMX:
                domainBackupMX = 'no'
            mod_attrs += [ (ldap.MOD_REPLACE, 'domainBackupMX', domainBackupMX) ]

            # Get domainRecipientBccAddress.
            domainRecipientBccAddress = web.safestr(data.get('domainRecipientBccAddress'))
            if domainRecipientBccAddress != 'None':
                mod_attrs += [ (ldap.MOD_REPLACE, 'domainRecipientBccAddress', domainRecipientBccAddress) ]

            # Get domainSenderBccAddress.
            domainSenderBccAddress = web.safestr(data.get('domainSenderBccAddress'))
            if domainSenderBccAddress != 'None':
                mod_attrs += [ (ldap.MOD_REPLACE, 'domainSenderBccAddress', domainSenderBccAddress) ]

            for i in ['domainMaxQuotaSize', 'domainMaxUserNumber', 'domainMaxAliasNumber',
                    'domainMaxListNumber',]:
                value = web.safestr(data.get(i))
                if value != '':
                    mod_attrs += [ (ldap.MOD_REPLACE, i, value) ]

            return {'dn': dn, 'mod_attrs': mod_attrs}
        elif accountType == 'user':
            pass
        elif accountType == 'maillist':
            pass
        elif accountType == 'alias':
            pass
    else:
        pass

# Generate hashed password from plain text.
def generatePasswd(password, pwscheme=iredutils.LDAP_DEFAULT_PASSWD_SCHEME,):
    pwscheme = pwscheme.upper()
    salt = os.urandom(8)
    if sys.version_info[1] < 5: # Python 2.5
        import sha
        if pwscheme == 'SSHA':
            h = sha.new(password)
            h.update(salt)
            pw = "{SSHA}" + b64encode( h.digest() + salt )
        elif pwscheme == 'SHA':
            h = sha.new(password)
            pw = "{SHA}" + b64encode( h.digest() )
        else:
            pw = password
    else:
        import hashlib
        if pwscheme == 'SSHA':
            h = hashlib.sha1(password)
            h.update(salt)
            pw = "{SSHA}" + b64encode( h.digest() + salt )
        elif pwscheme == 'SHA':
            h = hashlib.sha1(password)
            pw = "{SSHA}" + b64encode( h.digest() )
        else:
            pw = password

    return pw

# Check password.
def checkPassword(hashed_password, password):
    hashed_bytes = decode(hashed_password[6:])
    digest = hashed_bytes[:20]
    salt = hashed_bytes[20:]
    hr = hashlib.sha1(password)
    hr.update(salt)
    return digest == hr.digest()

def getLdifOfSingleAttr(attr, value, default='None'):
    if value is not None and value != '':
        ldif = [(attr, [value.encode('utf-8')])]
    else:
        ldif = [(attr, [default.encode('utf-8')])]

    return ldif

def getSingleModAttr(attr, value, default='None'):
    # Default value is string 'None', not None (NoneType).
    if value is not None and value != '' and value != u'':
        mod_attrs = [(ldap.MOD_REPLACE, attr, value.encode('utf-8'))]
    else:
        if default is not None and default != 'None':
            mod_attrs = [ ( ldap.MOD_REPLACE, attr, default.encode('utf-8') ) ]
        else:
            mod_attrs = [( ldap.MOD_REPLACE, attr, default )]

    return mod_attrs

def getExceptionDesc(e, key='msg'):
    if isinstance(e, types.InstanceType):
        try:
            if 'desc' in e.args[0].keys() and 'matched' in e.args[0].keys():
                msg = e.args[0]['desc'] + ': ' + e.args[0]['matched']
            else:
                msg = ''
                for k in ['info', 'desc', 'matched', ]:
                    if k in e.args[0].keys():
                        msg += e.args[0][k] + ' '
            return msg
        except:
            return str(e)
    else:
        return str(e)

def getAccountSettingFromLdapQueryResult(queryResult, key='domainName',):
    """Get account setting from LDAP query result. Return a dictionary.

    >>> queryResult = [
    ...         ('dn', {'var': ['value', 'value',], ... })
    ...     ]

    >>> allAccountSettings = {
    ...     'key': {
    ...             'var': 'value',
    ...             'var': 'value',
    ...             ...
    ...             },
    ...     ...
    ... }
    """
    allAccountSettings = {}
    if len(queryResult) > 0:
        for d in queryResult:
            if d[1].get('accountSetting', None) is not None:
                accountSettings = {}

                for setting in d[1]['accountSetting']:
                    if len(setting.split(':', 1)) == 2:
                        k, v = setting.split(':', 1)
                        if k in ['defaultQuota', 'minPasswordLength', 'maxPasswordLength', \
                                 'numberOfUsers', 'numberOfAliases', 'numberOfLists',]:
                            # Value of these settings must be interger.
                            if v.isdigit():
                                accountSettings[k] = v
                        else:
                            accountSettings[k] = v

                allAccountSettings[ d[1][key][0] ] = accountSettings

    return allAccountSettings
