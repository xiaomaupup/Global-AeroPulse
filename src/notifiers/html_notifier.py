"""
HTML page generator for AI News Bot

Generates a standalone, mobile-friendly HTML page for each news digest.
"""
import os
from datetime import datetime
from typing import Optional
from pathlib import Path
from ..logger import setup_logger


logger = setup_logger(__name__)


class HTMLNotifier:
    """Generate a standalone H5-style HTML page for the news digest."""

    def __init__(self, output_dir: str = "web"):
        """
        Initialize HTML notifier.

        Args:
            output_dir: Directory where HTML files will be written
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"HTMLNotifier initialized (output dir: {self.output_dir})")

    def send(self, content: str, subject: Optional[str] = None, language: str = "en") -> bool:
        """
        Generate an HTML file containing the news digest.

        Args:
            content: News digest in markdown / plain text format
            subject: Page title. If None, uses default with current date
            language: Language code to include in filename (e.g., 'en', 'zh')

        Returns:
            True if file generated successfully, False otherwise
        """
        try:
            # Default title
            if subject is None:
                today = datetime.now().strftime("%Y-%m-%d")
                lang_suffix = f" [{language.upper()}]" if language != "en" else ""
                subject = f"Aviation News Digest - {today}{lang_suffix}"

            html_content = self._create_html_page(content, subject)

            # File paths: one按日期归档，一个始终指向最新
            today_str = datetime.now().strftime("%Y%m%d")
            lang_code = language.lower()

            dated_filename = f"aviation_news_{today_str}_{lang_code}.html"
            latest_filename = f"latest_{lang_code}.html"

            dated_path = self.output_dir / dated_filename
            latest_path = self.output_dir / latest_filename

            for path in (dated_path, latest_path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(html_content)

            logger.info(
                f"HTML page generated: {dated_path} (also updated {latest_path})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to generate HTML page: {str(e)}", exc_info=True)
            return False

    def _create_html_page(self, content: str, title: str) -> str:
        """
        Create a mobile-friendly HTML page for the digest.

        Args:
            content: Markdown / plain text content
            title: Page title

        Returns:
            Full HTML document as string
        """
        # 尝试使用 markdown 转 HTML，方便保留层级结构
        try:
            import markdown

            html_body = markdown.markdown(
                content,
                extensions=[
                    "nl2br",
                    "tables",
                    "fenced_code",
                    "sane_lists",
                ],
            )
        except ImportError:
            import html as html_mod

            html_body = html_mod.escape(content).replace("\n", "<br>\n")

        # 移动端 H5 风格页面
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <title>{title}</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
                         "Segoe UI", "PingFang SC", "Microsoft YaHei",
                         Helvetica, Arial, sans-serif;
            background-color: #0f172a;
            color: #e5e7eb;
            line-height: 1.7;
        }}
        .page {{
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            background: radial-gradient(circle at top, #1d4ed8 0, #020617 55%);
        }}
        .header {{
            padding: 16px 16px 8px;
        }}
        .app-name {{
            font-size: 14px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #9ca3af;
        }}
        .title {{
            margin-top: 8px;
            font-size: 22px;
            font-weight: 700;
            color: #f9fafb;
        }}
        .subtitle {{
            margin-top: 4px;
            font-size: 13px;
            color: #9ca3af;
        }}
        .chip-row {{
            margin-top: 10px;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .chip {{
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 999px;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(148, 163, 184, 0.35);
            color: #cbd5f5;
        }}
        .content-wrapper {{
            flex: 1;
            margin-top: 4px;
            background: rgba(15, 23, 42, 0.9);
            border-top-left-radius: 18px;
            border-top-right-radius: 18px;
            box-shadow: 0 -8px 30px rgba(15, 23, 42, 0.9);
            padding: 16px 12px 24px;
        }}
        .content-inner {{
            max-width: 720px;
            margin: 0 auto;
        }}
        .content-inner h1 {{
            margin: 12px 4px 10px;
            font-size: 20px;
            color: #e5e7eb;
            border-left: 4px solid #3b82f6;
            padding-left: 10px;
        }}
        .content-inner h2 {{
            margin: 18px 4px 8px;
            font-size: 17px;
            color: #e5e7eb;
        }}
        .content-inner h3 {{
            margin: 14px 4px 6px;
            font-size: 15px;
            font-weight: 600;
            color: #bfdbfe;
        }}
        .content-inner p {{
            margin: 8px 4px;
            font-size: 14px;
            color: #e5e7eb;
        }}
        .content-inner ul,
        .content-inner ol {{
            margin: 8px 4px 8px 20px;
            font-size: 14px;
        }}
        .content-inner li {{
            margin: 4px 0;
        }}
        .content-inner a {{
            color: #60a5fa;
            text-decoration: none;
        }}
        .content-inner a:hover {{
            text-decoration: underline;
        }}
        .content-inner hr {{
            border: none;
            border-top: 1px solid rgba(55, 65, 81, 0.8);
            margin: 18px 0;
        }}
        .badge {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 999px;
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(96, 165, 250, 0.5);
            color: #bfdbfe;
        }}
        .footer {{
            margin-top: 20px;
            text-align: center;
            font-size: 11px;
            color: #6b7280;
        }}
        @media (min-width: 768px) {{
            .header {{
                padding: 20px 24px 12px;
            }}
            .content-wrapper {{
                padding: 20px 16px 28px;
            }}
        }}
    </style>
</head>
<body>
    <div class="page">
        <header class="header">
            <div class="app-name">COMAC · Aviation Insights</div>
            <h1 class="title">{title}</h1>
            <div class="subtitle">
                为市场营销与销售团队生成的每日航空热点简报 · 由 LLM 自动整理
            </div>
            <div class="chip-row">
                <span class="chip">民机制造 · 航空公司 · 适航监管 · 竞争对手</span>
                <span class="chip">自动汇总 · 非官方立场 · 请结合原文判断</span>
            </div>
        </header>
        <main class="content-wrapper">
            <div class="content-inner">
                {html_body}
                <div class="footer">
                    <p>本页面由 AI News Bot 自动生成，内容基于公开 RSS 新闻源。</p>
                    <p>不代表中国商飞官方立场，仅供内部研判与参考。</p>
                </div>
            </div>
        </main>
    </div>
</body>
</html>
"""
        return html

