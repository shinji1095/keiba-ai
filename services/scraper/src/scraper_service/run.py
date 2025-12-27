from __future__ import annotations

import os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from scraper_service.spiders.example_spider import ExampleSpider


def main() -> None:
    pc_api_url = os.getenv("PC_API_URL", "")
    _ = pc_api_url  # NOTE: 将来、取得結果をPC側APIへPOSTする用途で利用します。

    settings = get_project_settings()
    process = CrawlerProcess(settings)
    process.crawl(ExampleSpider)
    process.start()


if __name__ == "__main__":
    main()
