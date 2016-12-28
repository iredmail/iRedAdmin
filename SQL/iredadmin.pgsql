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
    event VARCHAR(20) NOT NULL DEFAULT '',
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

-- GRANT INSERT,UPDATE,DELETE,SELECT on sessions,log,updatelog to iredadmin;
-- GRANT UPDATE,USAGE,SELECT ON log_id_seq TO iredadmin;

-- Key-value store.
CREATE TABLE tracking (
    k VARCHAR(255) NOT NULL,
    v TEXT,
    time TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_tracking_k ON tracking (k);

-- Store <-> domain <-> verify_code used to verify domain ownership
CREATE TABLE domain_ownership (
    id SERIAL PRIMARY KEY,
    -- the admin who added this domain with iRedAdmin. Required if domain was
    -- added by a normal domain admin.
    admin VARCHAR(255) NOT NULL DEFAULT '',
    -- the domain we're going to verify. If we're going to verifying an alias
    -- domain, it stores primary domain.
    domain VARCHAR(255) NOT NULL DEFAULT '',
    -- if we're verifying an alias domain:
    --  - store primary domain in `domain`
    --  - store alias domain in `alias_domain`
    alias_domain VARCHAR(255) NOT NULL DEFAULT '',
    -- a unique string which domain admin should put in TXT type DNS record
    -- or as a web file on web server
    verify_code VARCHAR(100) NOT NULL DEFAULT '',
    -- store the verify status
    verified INT2 NOT NULL DEFAULT 0,
    -- store error message if any returned while verifying, so that domain
    -- admin can fix it
    message TEXT,
    -- the last time we verify it. If it's verified, this record will be
    -- removed in 1 month.
    last_verify TIMESTAMP NULL DEFAULT NULL,
    -- expire time. cron job `tools/cleanup_db.py` will remove verified or
    -- unverified domains regularly. e.g. one month.
    -- Note: stores seconds since Unix epoch
    expire INT DEFAULT 0
);
CREATE UNIQUE INDEX idx_ownership_1 ON domain_ownership (admin, domain, alias_domain);
CREATE INDEX idx_ownership_2 ON domain_ownership (verified);
