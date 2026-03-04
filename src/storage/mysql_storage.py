"""
MySQL storage utilities for AI News Bot.

Purpose:
- Store structured news items (after AI selection) into a MySQL table
- Designed to be optional: if MySQL is not configured, the rest of the bot still works
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List

from ..logger import setup_logger

logger = setup_logger(__name__)


def _get_mysql_config() -> Dict[str, str]:
    """Read MySQL configuration from environment variables."""
    cfg = {
        "host": os.getenv("MYSQL_HOST"),
        "port": os.getenv("MYSQL_PORT", "3306"),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DB"),
    }
    return cfg


def _is_config_complete(cfg: Dict[str, str]) -> bool:
    """Check whether all required MySQL configuration values exist."""
    required_keys = ["host", "user", "password", "database"]
    missing = [k for k in required_keys if not cfg.get(k)]
    if missing:
        logger.warning(
            "MySQL configuration incomplete, skipping DB storage. "
            f"Missing: {', '.join(missing)} (set MYSQL_HOST, MYSQL_USER, "
            "MYSQL_PASSWORD, MYSQL_DB in environment/.env)"
        )
        return False
    return True


def _get_connection():
    """
    Get a MySQL connection using PyMySQL.

    Returns:
        A PyMySQL connection instance.
    """
    import pymysql  # Imported lazily so project can run without MySQL if unused

    cfg = _get_mysql_config()
    if not _is_config_complete(cfg):
        return None

    try:
        conn = pymysql.connect(
            host=cfg["host"],
            port=int(cfg["port"]),
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to MySQL: {e}")
        return None


def init_mysql_schema() -> bool:
    """
    Create the news_items table if it does not exist.

    Table schema (simplified for analytics and display):
        id            - auto increment primary key
        capture_date  - date when the bot captured this item (YYYY-MM-DD)
        language      - language code (e.g., 'zh', 'en')
        source_name   - RSS source display name
        title         - news title
        summary       - short description / intro (from RSS or AI-refined)
        url           - original article URL
        published_at  - original publish time string (as provided by RSS)
        created_at    - timestamp when record inserted
    """
    conn = _get_connection()
    if conn is None:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS news_items (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    capture_date DATE NOT NULL,
                    language VARCHAR(8) NOT NULL,
                    source_name VARCHAR(255) NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    url TEXT,
                    published_at VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_capture_date_lang (capture_date, language)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
                """
            )
        logger.info("MySQL schema ensured: news_items table is ready")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize MySQL schema: {e}", exc_info=True)
        return False
    finally:
        conn.close()


def save_news_items_to_mysql(
    language: str,
    items: List[Dict[str, str]],
) -> bool:
    """
    Save a batch of selected news items into MySQL.

    Args:
        language: Language code (e.g., 'zh')
        items: List of dicts with keys: title, description, source, link, published

    Returns:
        True if insert succeeded (or MySQL is not configured), False if hard failure.
    """
    cfg = _get_mysql_config()
    if not _is_config_complete(cfg):
        # Treat as "not an error" so the main flow still passes
        return False

    if not items:
        logger.info("No news items to store in MySQL, skipping insert")
        return True

    if not init_mysql_schema():
        # Schema creation failed; already logged
        return False

    conn = _get_connection()
    if conn is None:
        return False

    today = datetime.utcnow().date()

    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO news_items
                    (capture_date, language, source_name, title, summary, url, published_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s)
            """
            data = []
            for item in items:
                data.append(
                    (
                        today,
                        language.lower(),
                        item.get("source", "")[:255],
                        item.get("title", ""),
                        item.get("description", ""),
                        item.get("link", ""),
                        item.get("published", ""),
                    )
                )

            cur.executemany(sql, data)

        logger.info(f"Stored {len(items)} news items into MySQL for {today} ({language})")
        return True
    except Exception as e:
        logger.error(f"Failed to insert news items into MySQL: {e}", exc_info=True)
        return False
    finally:
        conn.close()

