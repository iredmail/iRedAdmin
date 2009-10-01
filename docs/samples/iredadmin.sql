#CREATE DATABASE iredadmin DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
#GRANT INSERT,UPDATE,DELETE,SELECT on iredadmin.* to iredadmin@localhost identified by 'secret_passwd';
#USE iredadmin;

#
# Session table required by webpy session module.
#
CREATE TABLE sessions (
    session_id CHAR(128) UNIQUE NOT NULL,
    atime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data TEXT,
    INDEX session_id_index (session_id)
) ENGINE=MyISAM;
