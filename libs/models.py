# encoding: utf-8
# Author: Zhang Huangbin <zhb@iredmail.org>

# SQL model of table: used_quota. Used in dovecot-1.2 for dictquota.
class UsedQuota:
    __table__ = 'used_quota'
    username = 'username'
    bytes = 'bytes'
    messages = 'messages'


# Models of MySQL backend.
class MysqlUserPass:
    username = 'username'
    password = 'password'


class MysqlPublic:
    created = 'created'
    modified = 'modified'
    expired = 'expired'
    active = 'active'


class MysqlAdmin(MysqlUserPass, MysqlPublic):
    __table__ = 'admin'
    language = 'language'


class MysqlAlias(MysqlPublic):
    __table__ = 'alias'
    address = 'address'
    goto = 'goto'
    moderators = 'moderators'
    accesspolicy = 'accesspolicy'
    domain = 'domain'


class MysqlDomain(MysqlPublic):
    __table__ = 'domain'
    domain = 'domain'
    description = 'description'
    disclaimer = 'disclaimer'
    aliases = 'aliases'
    mailboxes = 'mailboxes'
    maxquota = 'maxquota'
    quota = 'quota'
    transport = 'transport'
    backupmx = 'backupmx'
    defaultuserquota = 'defaultuserquota'
    minpasswordlength = 'minpasswordlength'
    maxpasswordlength = 'maxpasswordlength'


class MysqlAliasDomain(MysqlPublic):
    __table__ = 'alias_domain'
    alias_domain = 'alias_domain'
    target_domain = 'target_domain'


class MysqlDomainAdmins(MysqlPublic):
    __table__ = 'domain_admins'
    username = 'username'
    domain = 'domain'


class MysqlMailbox(MysqlUserPass, MysqlPublic):
    __table__ = 'mailbox'
    name = 'name'
    storagebasedirectory = 'storagebasedirectory'
    storagenode = 'storagenode'
    maildir = 'maildir'
    quota = 'quota'
    bytes = 'bytes'
    messages = 'messages'
    domain = 'domain'
    transport = 'transport'
    department = 'department'
    rank = 'rank'
    employeeid = 'employeeid'
    enablesmtp = 'enablesmtp'
    enablepop3 = 'enablepop3'
    enablepop3secured = 'enablepop3secured'
    enableimap = 'enableimap'
    enableimapsecured = 'enableimapsecured'
    enabledeliver = 'enabledeliver'
    enablemanagesieve = 'enablemanagesieve'
    enablemanagesievesecured = 'enablemanagesievesecured'
    enablesieve = 'enablesieve'
    enablesievesecured = 'enablesievesecured'
    enableinternal = 'enableinternal'
    lastlogindate = 'lastlogindate'
    lastloginipv4 = 'lastloginipv4'
    lastloginprotocol = 'lastloginprotocol'
    disclaimer = 'disclaimer'
    local_part = 'local_part'   # Required by PostfixAdmin


class MysqlSenderBccDomain(MysqlPublic):
    __table__ = 'sender_bcc_domain'
    domain = 'domain'
    bcc_address = 'bcc_address'


class MysqlSenderBccUser(MysqlPublic):
    __table__ = 'sender_bcc_user'
    username = 'username'
    bcc_address = 'bcc_address'
    domain = 'domain'


class MysqlReipientBccDomain(MysqlPublic):
    __table__ = 'recipient_bcc_domain'
    domain = 'domain'
    bcc_address = 'bcc_address'


class MysqlReipientBccUser(MysqlPublic):
    __table__ = 'recipient_bcc_user'
    username = 'username'
    bcc_address = 'bcc_address'
    domain = 'domain'

