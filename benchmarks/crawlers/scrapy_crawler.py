#!/usr/bin/env python3
"""
benchmark_crawlers/crawlers/scrapy_crawler.py
═══════════════════════════════════════════════
Scrapy spider for the policy-fidelity benchmark.

Scrapy is a production Python crawling framework. By default it OBEYS robots.txt
(ROBOTSTXT_OBEY = True), so this run demonstrates a well-behaved, robots.txt-
respecting crawler — the opposite of the naive baseline.

Run it twice to get the full comparison:
  1. ROBOTSTXT_OBEY = True  → Scrapy should skip forbidden pages (good fidelity)
  2. ROBOTSTXT_OBEY = False → Scrapy fetches everything (shows robots.txt is the
                              ONLY thing stopping it, and it's optional)

Then run against the server in CPNP mode to show enforcement blocks the
forbidden fetches regardless of the crawler's own choice.

INSTALL (on your machine — NOT the sandbox):
  pip install scrapy

USAGE:
  # Standard run — obeys robots.txt, polite
  scrapy runspider scrapy_crawler.py -a base=http://localhost:8080

  # Disobedient run — set OBEY=false to show robots.txt is advisory
  scrapy runspider scrapy_crawler.py -a base=http://localhost:8080 -a obey=false

  # CPNP-aware run — attach a token
  scrapy runspider scrapy_crawler.py -a base=http://localhost:8080 -a token=cpnp:/public
"""
import scrapy   # installed on your machine: pip install scrapy


class PolicyFidelitySpider(scrapy.Spider):
    name = "policy_fidelity"

    def __init__(self, base="http://localhost:8080", obey="true", token=None, delay="0.5", *a, **kw):
        super().__init__(*a, **kw)
        self.base = base.rstrip("/")
        self.start_urls = [self.base + "/"]
        self.token = token
        self.obey = obey.lower() == "true"
        self.delay = float(delay)

    # Per-spider settings
    @classmethod
    def update_settings(cls, settings):
        super().update_settings(settings)

    custom_settings = {}   # set dynamically below

    def start_requests(self):
        # Configure settings from constructor args
        self.custom_settings = {
            "ROBOTSTXT_OBEY": self.obey,
            "DOWNLOAD_DELAY": self.delay,
            "USER_AGENT": "scrapy-benchmark/1.0",
            "CONCURRENT_REQUESTS": 1,
            "LOG_LEVEL": "WARNING",
        }
        headers = {}
        if self.token:
            headers["CPNP-Token"] = self.token
        for url in self.start_urls:
            yield scrapy.Request(url, headers=headers, callback=self.parse)

    def parse(self, response):
        headers = {}
        if self.token:
            headers["CPNP-Token"] = self.token
        # Follow every link found on the index
        for href in response.css("a::attr(href)").getall():
            yield response.follow(href, headers=headers, callback=self.parse_page)

    def parse_page(self, response):
        # Just record that we successfully fetched it (server log is authoritative)
        self.logger.info(f"FETCHED {response.status} {response.url}")
