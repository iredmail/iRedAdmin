#
# Session table required by webpy session module.
#
CREATE TABLE sessions (
    session_id CHAR(128) UNIQUE NOT NULL,
    atime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data TEXT,
    INDEX session_id_index (session_id)
) TYPE=MyISAM;
