"""
Supabase HTTP storage utilities for AI News Bot.

通过 Supabase 提供的 REST 接口，把选中的结构化新闻写入 Postgres 表。
优点：不需要直连数据库（5432 端口），只要能访问 https://*.supabase.co 即可。
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List

import requests

from ..logger import setup_logger

logger = setup_logger(__name__)


def _get_supabase_config() -> Dict[str, str]:
    """从环境变量中读取 Supabase 配置。"""
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    return {
        "url": url,
        "key": key or "",
    }


def save_news_items_to_supabase(
    language: str,
    items: List[Dict[str, str]],
) -> bool:
    """
    通过 Supabase REST 接口，把新闻条目写入 news_items 表。

    表结构推荐（在 Supabase 里用 SQL 手动建表）：

        create table if not exists public.news_items (
          id           bigserial primary key,
          capture_date date        not null,
          language     varchar(8)  not null,
          source_name  text        not null,
          title        text        not null,
          summary      text,
          url          text,
          published_at text,
          created_at   timestamptz not null default now()
        );
        create index if not exists idx_news_items_capture_date_lang
          on public.news_items (capture_date, language);

    Args:
        language: 语言代码（如 'zh'）
        items: 若干新闻 dict，字段包含：title, description, source, link, published

    Returns:
        True 表示调用成功（2xx），False 表示失败或未配置。
    """
    cfg = _get_supabase_config()
    if not cfg["url"] or not cfg["key"]:
        logger.warning(
            "Supabase URL / SERVICE_KEY not configured, skip Supabase storage. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env to enable."
        )
        return False

    if not items:
        logger.info("No news items to store in Supabase, skipping insert")
        return True

    endpoint = f"{cfg['url']}/rest/v1/news_items"

    today = datetime.utcnow().date().isoformat()
    payload = []
    for item in items:
        payload.append(
            {
                "capture_date": today,
                "language": language.lower(),
                "source_name": item.get("source", ""),
                "title": item.get("title", ""),
                "summary": item.get("description", ""),
                "url": item.get("link", ""),
                "published_at": item.get("published", ""),
            }
        )

    headers = {
        "apikey": cfg["key"],
        "Authorization": f"Bearer {cfg['key']}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    try:
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=15)
        if 200 <= resp.status_code < 300:
            logger.info(
                f"Stored {len(items)} news items into Supabase (news_items, {today}, {language})"
            )
            return True

        logger.error(
            f"Supabase insert failed: {resp.status_code} {resp.text}"
        )
        return False
    except Exception as e:
        logger.error(f"Error calling Supabase REST API: {e}", exc_info=True)
        return False

