-- CREATE DATABASE iredadmin WITH TEMPLATE template0 ENCODING 'UTF8';
-- CREATE ROLE iredadmin WITH LOGIN ENCRYPTED PASSWORD 'plain_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
-- \c iredadmin;

-- Session table required by webpy session module.
CREATE TABLE sessions (
    session_id CHAR(128) UNIQUE NOT NULL,
    atime TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data TEXT
);

-- Store all admin operations.
CREATE TABLE log (
    id SERIAL PRIMARY KEY,
    admin VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip VARCHAR(40) NOT NULL,
    domain VARCHAR(255) NOT NULL DEFAULT '',
    username VARCHAR(255) NOT NULL DEFAULT '',
    event VARCHAR(10) NOT NULL DEFAULT '',
    loglevel VARCHAR(10) NOT NULL DEFAULT 'info',
    msg VARCHAR(255) NOT NULL
);

CREATE INDEX idx_log_timestamp ON log (timestamp);                                            
CREATE INDEX idx_log_ip ON log (ip);
CREATE INDEX idx_log_domain ON log (domain);
CREATE INDEX idx_log_username ON log (username);
CREATE INDEX idx_log_event ON log (event);
CREATE INDEX idx_log_loglevel ON log (loglevel);

CREATE TABLE updatelog (
    date DATE NOT NULL,
    PRIMARY KEY (date)
);

-- Used to store basic info of deleted mailboxes.
CREATE TABLE deleted_mailboxes (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Email address of deleted user
    username VARCHAR(255) NOT NULL DEFAULT '',
    -- Domain part of user email address
    domain VARCHAR(255) NOT NULL DEFAULT '',
    -- Absolute path of user's mailbox
    maildir VARCHAR(255) NOT NULL DEFAULT '',
    -- Which domain admin deleted this user
    admin VARCHAR(255) NOT NULL DEFAULT ''
);

CREATE INDEX idx_deleted_mailboxes_timestamp ON deleted_mailboxes (timestamp);
CREATE INDEX idx_deleted_mailboxes_username ON deleted_mailboxes (username);
CREATE INDEX idx_deleted_mailboxes_domain ON deleted_mailboxes (domain);
CREATE INDEX idx_deleted_mailboxes_admin ON deleted_mailboxes (admin);

-- GRANT INSERT,UPDATE,DELETE,SELECT on sessions,log,updatelog to iredadmin;
-- GRANT UPDATE,USAGE,SELECT ON log_id_seq TO iredadmin;
