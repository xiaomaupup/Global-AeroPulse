"""
PostgreSQL (Supabase) storage utilities for AI News Bot.

用途：
- 把经过 AI 选择的结构化新闻条目，写入 Supabase 提供的 Postgres 数据库
- 完全可选：如果没有配置连接串，主流程照常运行，只是不入库
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List

from ..logger import setup_logger

logger = setup_logger(__name__)


def _get_pg_dsn() -> str | None:
    """
    从环境变量里读取 Postgres 连接串。

    优先使用 POSTGRES_DSN，其次 DATABASE_URL。
    例如（Supabase）：
    postgresql://postgres:YOUR-PASSWORD@db.xxx.supabase.co:5432/postgres
    """
    dsn = os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL")
    if not dsn:
        logger.warning(
            "Postgres DSN not configured, skipping DB storage. "
            "Set POSTGRES_DSN in .env to enable Supabase/Postgres persistence."
        )
        return None
    return dsn


def _get_connection():
    """
    建立到 Postgres 的连接（使用 psycopg2）。

    返回 psycopg2 connection，如果失败则返回 None。
    """
    import psycopg2  # 惰性导入，避免没装依赖时主流程直接崩溃

    dsn = _get_pg_dsn()
    if not dsn:
        return None

    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to Postgres: {e}")
        return None


def init_postgres_schema() -> bool:
    """
    确保 news_items 表已存在，不存在则创建。

    建议你在 Supabase 里使用同样结构：

      id           BIGSERIAL PRIMARY KEY
      capture_date DATE NOT NULL
      language     VARCHAR(8) NOT NULL
      source_name  TEXT NOT NULL
      title        TEXT NOT NULL
      summary      TEXT
      url          TEXT
      published_at TEXT
      created_at   TIMESTAMPTZ DEFAULT NOW()
      INDEX (capture_date, language)
    """
    conn = _get_connection()
    if conn is None:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS news_items (
                    id BIGSERIAL PRIMARY KEY,
                    capture_date DATE NOT NULL,
                    language VARCHAR(8) NOT NULL,
                    source_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    url TEXT,
                    published_at TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_news_items_capture_date_lang
                    ON news_items (capture_date, language);
                """
            )
        logger.info("Postgres schema ensured: news_items table is ready")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Postgres schema: {e}", exc_info=True)
        return False
    finally:
        conn.close()


def save_news_items_to_postgres(
    language: str,
    items: List[Dict[str, str]],
) -> bool:
    """
    批量写入选中的新闻条目到 Postgres/Supabase。

    Args:
        language: 语言代码（如 'zh'）
        items: 若干新闻 dict，字段包含：title, description, source, link, published

    Returns:
        True 表示写入成功（或者未配置 DSN 时跳过），False 表示硬失败。
    """
    dsn = _get_pg_dsn()
    if not dsn:
        # 视为“未启用持久化”，不是致命错误
        return False

    if not items:
        logger.info("No news items to store in Postgres, skipping insert")
        return True

    if not init_postgres_schema():
        return False

    import psycopg2

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
                        item.get("source", ""),
                        item.get("title", ""),
                        item.get("description", ""),
                        item.get("link", ""),
                        item.get("published", ""),
                    )
                )

            cur.executemany(sql, data)

        logger.info(
            f"Stored {len(items)} news items into Postgres for {today} ({language})"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to insert news items into Postgres: {e}", exc_info=True)
        return False
    finally:
        conn.close()

