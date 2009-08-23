# CREATE DATABASE iredadmin DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
# GRANT INSERT,UPDATE,DELETE,SELECT on iredadmin.* to iredadmin@localhost identified by 'secret_passwd';
#USE iredadmin;

#
# Session table required by webpy session module.
#
CREATE TABLE sessions (
    session_id CHAR(128) UNIQUE NOT NULL,
    atime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data TEXT,
    INDEX session_id_index (session_id)
) TYPE=MyISAM;

#
# Store all operations.
#
CREATE TABLE log (
    timestamp DATETIME NOT NULL DEFAULT '0000-00-00 00:00:00',
    admin VARCHAR(255) NOT NULL DEFAULT '',
    domain VARCHAR(255) NOT NULL DEFAULT '',
    action VARCHAR(255) NOT NULL DEFAULT '',
    data VARCHAR(255) NOT NULL DEFAULT '',
    KEY TIMESTAMP (TIMESTAMP),
    INDEX timestamp_index (timestamp),
    INDEX admin_index (admin),
    INDEX domain_index (domain),
    INDEX action_index (action)
) TYPE=MyISAM;

#
# author: Who public this announcement.
# admins: Who will see this announcement. Default is ALL admins.
#         Multiple admins should be seperated by comma.
# starttime: When this ann msg will be displayed. Default is NOW.
# endtime:   When it should not be displayed.
# subject: message subject.
# message: content of ann msg.
#
CREATE TABLE announcements (
    id INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
    author VARCHAR(250) NOT NULL,
    admins VARCHAR(250) NOT NULL DEFAULT 'ALL',
    starttime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, 
    endtime TIMESTAMP,
    subject VARCHAR(250) NOT NULL,
    message text NOT NULL,
    PRIMARY KEY (id),
    INDEX id_index (id),
    INDEX author_index (author),
    INDEX admins_index (admins),
    INDEX starttime_index (starttime),
    INDEX endtime_index (endtime)
) TYPE=MyISAM;
