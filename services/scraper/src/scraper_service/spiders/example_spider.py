from __future__ import annotations

import scrapy


class ExampleSpider(scrapy.Spider):
    name = "example"
    allowed_domains = ["example.com"]
    start_urls = ["https://example.com/"]

    def parse(self, response: scrapy.http.Response):
        title = response.css("title::text").get() or ""
        yield {"title": title}
