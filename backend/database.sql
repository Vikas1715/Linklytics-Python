-- =====================================================
-- Linklytics (Python version) - Database Schema
-- =====================================================
-- Run this once to create the database and tables:
--   mysql -u root -p < database.sql
-- =====================================================

CREATE DATABASE IF NOT EXISTS linklytics_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE linklytics_db;

-- Stores registered users
CREATE TABLE IF NOT EXISTS users (
    id          INT          NOT NULL AUTO_INCREMENT,
    username    VARCHAR(50)  NOT NULL,
    email       VARCHAR(100) NOT NULL,
    password    VARCHAR(255) NOT NULL,   -- stores the bcrypt HASH, never plain text
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email    (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Stores shortened URLs, one row per short link
CREATE TABLE IF NOT EXISTS urls (
    id            INT           NOT NULL AUTO_INCREMENT,
    original_url  VARCHAR(2048) NOT NULL,
    short_code    VARCHAR(10)   NOT NULL,
    click_count   INT           NOT NULL DEFAULT 0,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_accessed DATETIME               DEFAULT NULL,
    user_id       INT           NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_short_code (short_code),
    INDEX idx_user_id (user_id),
    CONSTRAINT fk_url_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SELECT 'Database ready!' AS status;
