"""
AI News Generator using configurable LLM providers
"""
from typing import List, Optional, Dict
import json
import re
from datetime import datetime, timezone, timedelta
from ..logger import setup_logger
from ..config import LANGUAGE_NAMES
from .web_search import WebSearchTool, get_search_tool_definition
from .fetcher import NewsFetcher
from ..llm_providers import get_llm_provider
from ..storage.supabase_storage import save_news_items_to_supabase


logger = setup_logger(__name__)


class NewsGenerator:
    """Generate AI news digest using configurable LLM providers"""

    def __init__(
        self,
        provider_name: str = "claude",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        enable_web_search: bool = False
    ):
        """
        Initialize the NewsGenerator.

        Args:
            provider_name: Name of LLM provider to use ('claude' or 'deepseek')
            api_key: API key for the provider. If None, will read from environment
            model: Model name to use. If None, uses provider's default model
            enable_web_search: Whether to enable web search tool for fetching current news

        Raises:
            ValueError: If provider is not recognized or API key is not provided
        """
        # Initialize LLM provider
        self.provider = get_llm_provider(
            provider_name=provider_name,
            api_key=api_key,
            model=model
        )

        self.enable_web_search = enable_web_search
        self.search_tool = WebSearchTool() if enable_web_search else None
        self.news_fetcher = NewsFetcher()
        logger.info(
            f"NewsGenerator initialized with {self.provider.provider_name} "
            f"(model: {self.provider.model}, web_search: {enable_web_search})"
        )

    def _translate_text(self, text: str, target_language: str = "zh") -> str:
        """
        Use the configured LLM provider to translate text into target_language.
        Currently used to translate RSS 英文标题 / 简介为中文，便于列表展示。

        If translation fails for any reason, returns original text.
        """
        if not text.strip():
            return text

        try:
            # 为了避免 prompt 太长，这里限制单段长度
            snippet = text.strip()
            if len(snippet) > 800:
                snippet = snippet[:800]

            prompt = (
                "请将下面这段英文航空新闻内容翻译成自然流畅的简体中文，用于内部市场简报列表展示；"
                "保留公司名、机型名、地名等专有名词的英文写法，只返回译文正文，不要添加任何说明。\n\n"
                f"原文：\n{snippet}"
            )
            messages = [{"role": "user", "content": prompt}]
            translated = self.provider.generate(messages=messages, max_tokens=600)
            # 简单清理一下首尾空白
            return translated.strip()
        except Exception as e:
            logger.warning(f"Translation failed, fallback to original text: {e}")
            return text

    def _format_news_with_ids(self, news_data: Dict) -> tuple:
        """
        Format news with unique IDs for selection stage.

        Args:
            news_data: Dictionary with 'international' and 'domestic' news lists

        Returns:
            Tuple of (formatted_text, news_items_dict)
        """
        formatted = "# Recent AI News Items for Selection\n\n"
        news_items = {}  # id -> full news item
        item_id = 1

        if news_data['international']:
            formatted += "## International News\n\n"
            for item in news_data['international']:
                news_id = f"INT-{item_id}"
                news_items[news_id] = item

                formatted += f"### [{news_id}] {item['title']}\n"
                formatted += f"**Source:** {item['source']}\n"
                if item['description']:
                    formatted += f"**Description:** {item['description'][:400]}...\n"
                if item['published']:
                    formatted += f"**Published:** {item['published']}\n"
                formatted += "\n"
                item_id += 1

        if news_data['domestic']:
            formatted += "## Domestic News\n\n"
            item_id = 1
            for item in news_data['domestic']:
                news_id = f"DOM-{item_id}"
                news_items[news_id] = item

                formatted += f"### [{news_id}] {item['title']}\n"
                formatted += f"**Source:** {item['source']}\n"
                if item['description']:
                    formatted += f"**Description:** {item['description'][:400]}...\n"
                if item['published']:
                    formatted += f"**Published:** {item['published']}\n"
                formatted += "\n"
                item_id += 1

        return formatted, news_items

    def _enforce_freshness_strict(
        self,
        items: List[Dict[str, str]],
        hours_back: Optional[int],
        keep_undated: bool,
    ) -> List[Dict[str, str]]:
        """
        严格新鲜度校验（最终兜底）。
        - hours_back=None: 不做时间过滤
        - keep_undated=False: 解析不出时间的一律丢弃
        """
        if hours_back is None or hours_back <= 0:
            return items

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        kept: List[Dict[str, str]] = []
        dropped_old = 0
        dropped_undated = 0

        for item in items:
            dt = self.news_fetcher._parse_published_date(item.get("published", ""))
            if dt is None:
                if keep_undated:
                    kept.append(item)
                else:
                    dropped_undated += 1
                continue
            if dt >= cutoff:
                kept.append(item)
            else:
                dropped_old += 1

        if dropped_old or dropped_undated:
            logger.warning(
                f"Strict freshness enforced ({hours_back}h): dropped_old={dropped_old}, "
                f"dropped_undated={dropped_undated}, kept={len(kept)}"
            )

        return kept

    def generate_news_digest_from_sources(
        self,
        max_tokens: int = 8000,
        language: str = "en",
        max_items_per_source: int = 5,
        stage1_template: Optional[str] = None,
        stage2_template: Optional[str] = None
    ) -> str:
        """
        Fetch real-time news and generate a digest using two-stage prompt chaining:
        Stage 1: Analyze and select 15-20 high-quality news items
        Stage 2: Create detailed summaries for selected items

        Args:
            max_tokens: Maximum tokens in response
            language: Language code for the response
            max_items_per_source: Maximum items to fetch per source
            stage1_template: Optional Stage 1 prompt template (from config)
            stage2_template: Optional Stage 2 prompt template (from config)

        Returns:
            Generated news digest as string

        Raises:
            Exception: If fetching or generation fails
        """
        try:
            # Fetch real-time news（仅保留最近 N 小时内发布的，由 config 的 max_hours_back 控制）
            from ..config import Config
            _config = Config()
            hours_back = _config.max_hours_back
            keep_undated = _config.keep_undated
            logger.info("Fetching real-time AI news from sources...")
            news_data = self.news_fetcher.fetch_recent_news(
                language=language,
                max_items_per_source=max_items_per_source,
                hours_back=hours_back,
                keep_undated=keep_undated,
            )

            if not news_data['international'] and not news_data['domestic']:
                # 严格要求：宁可日报为空，也不要混入旧新闻
                logger.warning(
                    f"No news items within freshness window (hours_back={hours_back}, keep_undated={keep_undated}). "
                    f"Return empty digest."
                )
                if language and language.lower() == "zh":
                    return "## 今日航空日报\n\n过去 24 小时内未抓取到符合条件的全球航空热点新闻（已严格丢弃旧闻与无发布时间新闻）。"
                return "## Aviation Daily Digest\n\nNo qualifying news items were found in the last 24 hours (old/undated items were strictly discarded)."

            # Format news with unique IDs for selection
            formatted_news, news_items = self._format_news_with_ids(news_data)
            total_items = len(news_items)

            logger.info(f"Starting two-stage prompt chaining with {total_items} news items")

            # ============================================================
            # STAGE 1: Selection - Analyze and select 15-20 best items
            # ============================================================
            logger.info(f"Stage 1: Analyzing and selecting high-quality news items...")

            # Use provided template or load from config
            if stage1_template is None:
                from ..config import Config
                config = Config()
                stage1_template = config.stage1_prompt_template

            # Format Stage 1 prompt with placeholders
            selection_prompt = stage1_template.format(
                formatted_news=formatted_news,
                total_items=total_items
            )

            messages = [{"role": "user", "content": selection_prompt}]
            selection_response = self.provider.generate(
                messages=messages,
                max_tokens=4000 # give enough tokens for selection
            )

            # Parse selected IDs
            json_match = re.search(r'\[[\s\S]*?\]', selection_response)
            if not json_match:
                logger.warning("Could not parse JSON from selection response, using fallback")
                # Fallback: select first 18 items
                selected_ids = list(news_items.keys())[:18]
            else:
                try:
                    selected_ids = json.loads(json_match.group(0))
                    # Validate IDs
                    selected_ids = [id for id in selected_ids if id in news_items]

                    # Ensure we have 15-20 items
                    if len(selected_ids) < 15:
                        logger.warning(f"Only {len(selected_ids)} items selected, adding more")
                        remaining = [id for id in news_items.keys() if id not in selected_ids]
                        selected_ids.extend(remaining[:18 - len(selected_ids)])
                    elif len(selected_ids) > 20:
                        logger.warning(f"{len(selected_ids)} items selected, trimming to 20")
                        selected_ids = selected_ids[:20]

                except json.JSONDecodeError:
                    logger.warning("JSON parse error, using fallback selection")
                    selected_ids = list(news_items.keys())[:18]

            logger.info(f"Stage 1 completed: Selected {len(selected_ids)} news items")
            logger.debug(f"Selected IDs: {selected_ids}")

            # After Stage 1: store structured selected items into Supabase (if configured)
            selected_items_for_storage = []
            for news_id in selected_ids:
                item = news_items[news_id]
                # 为列表展示准备结构化数据：如果目标语言是中文，则在入库前做一次标题/简介翻译
                item_for_storage = dict(item)
                if language and language.lower() == "zh":
                    item_for_storage["title"] = self._translate_text(
                        item_for_storage.get("title", ""), target_language="zh"
                    )
                    item_for_storage["description"] = self._translate_text(
                        item_for_storage.get("description", ""), target_language="zh"
                    )

                selected_items_for_storage.append(item_for_storage)

            if selected_items_for_storage:
                # 入库前最后兜底：再次严格校验“发布时间在窗口内”
                selected_items_for_storage = self._enforce_freshness_strict(
                    selected_items_for_storage,
                    hours_back=hours_back,
                    keep_undated=keep_undated,
                )

            if selected_items_for_storage:
                save_news_items_to_supabase(
                    language=language,
                    items=selected_items_for_storage,
                )
            else:
                logger.warning("After strict freshness check, 0 items left to store. Skip Supabase storage.")

            # ============================================================
            # STAGE 2: Summarization - Create detailed summaries
            # ============================================================
            logger.info(f"Stage 2: Creating detailed summaries for selected items...")

            # Format selected news for summarization
            formatted_selected = "# Selected High-Quality AI News Items\n\n"
            for news_id in selected_ids:
                item = news_items[news_id]
                formatted_selected += f"### [{news_id}] {item['title']}\n"
                formatted_selected += f"**Source:** {item['source']}\n"
                if item['description']:
                    formatted_selected += f"**Content:** {item['description']}\n"
                formatted_selected += f"**Link:** {item['link']}\n"
                if item['published']:
                    formatted_selected += f"**Published:** {item['published']}\n"
                formatted_selected += "\n"

            # Use provided template or load from config
            if stage2_template is None:
                from ..config import Config
                config = Config()
                stage2_template = config.stage2_prompt_template

            # Format Stage 2 prompt with placeholders
            summarization_prompt = stage2_template.format(
                count=len(selected_ids),
                selected_news=formatted_selected
            )

            # Add language instruction if not English
            if language and language.lower() != "en":
                language_name = LANGUAGE_NAMES.get(language.lower(), language.upper())
                summarization_prompt += f"\n\nIMPORTANT: Please respond entirely in {language_name}."

            # Execute Stage 2: Generate detailed summaries
            messages = [{"role": "user", "content": summarization_prompt}]
            response_text = self.provider.generate(
                messages=messages,
                max_tokens=max_tokens
            )

            # Add footer with GitHub link
            footer = "\n\n---\n\n*Generated by [AI News Bot](https://github.com/giftedunicorn/ai-news-bot) - Your AI-powered news assistant*"
            response_text += footer

            logger.info("Stage 2 completed: News digest generated successfully")
            logger.info(f"Two-stage prompt chaining completed: {total_items} items → {len(selected_ids)} selected → full digest")
            logger.debug(f"Response length: {len(response_text)} characters")

            return response_text

        except Exception as e:
            logger.error(f"Failed to generate news digest from sources: {str(e)}", exc_info=True)
            raise
