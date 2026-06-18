"""
cpnp/audit/website_list.py
────────────────────────────
The 50 real websites for the robots.txt expressiveness audit.

SELECTION METHODOLOGY :
The 50 sites were selected using STRATIFIED PURPOSIVE SAMPLING across six
categories that represent the populations most affected by the AI-crawling
governance crisis (Longpre et al., 2024; Kim et al., 2025). Each category
has a different incentive structure around crawl control, so sampling across
them tests whether the robots.txt expressiveness gap is universal or
category-specific.

Categories and rationale:
  1. News & Publishing (10) — highest-profile AI-data disputes; most likely
     to have sophisticated, restrictive robots.txt (NYT, Guardian, etc.)
  2. Academic & Research (8) — repositories whose consent terms matter for
     scholarly data; your own domain
  3. E-commerce & Reviews (8) — high commercial value, data-resale concerns
  4. Social & Community (8) — user-generated content, consent-sensitive
  5. Reference & Knowledge (8) — high crawl-target value (Wikipedia, etc.)
  6. Government & Institutional (8) — public-interest, jurisdiction-sensitive

This stratification lets you report findings per category and in aggregate,
strengthening external validity.

NOTE: All robots.txt files are public documents served at /robots.txt.
Fetching them is standard, ethical, and explicitly permitted — it is the
mechanism the web provides for exactly this purpose. No site content is
crawled; only the public policy file is read.
"""

WEBSITES = [
    # ── 1. News & Publishing ──────────────────────────────────────────────
    ("nytimes.com",        "News & Publishing", "https://www.nytimes.com/robots.txt"),
    ("theguardian.com",    "News & Publishing", "https://www.theguardian.com/robots.txt"),
    ("bbc.com",            "News & Publishing", "https://www.bbc.com/robots.txt"),
    ("reuters.com",        "News & Publishing", "https://www.reuters.com/robots.txt"),
    ("washingtonpost.com", "News & Publishing", "https://www.washingtonpost.com/robots.txt"),
    ("cnn.com",            "News & Publishing", "https://www.cnn.com/robots.txt"),
    ("forbes.com",         "News & Publishing", "https://www.forbes.com/robots.txt"),
    ("bloomberg.com",      "News & Publishing", "https://www.bloomberg.com/robots.txt"),
    ("nation.africa",      "News & Publishing", "https://nation.africa/robots.txt"),
    ("standardmedia.co.ke","News & Publishing", "https://www.standardmedia.co.ke/robots.txt"),

    # ── 2. Academic & Research ────────────────────────────────────────────
    ("arxiv.org",          "Academic & Research", "https://arxiv.org/robots.txt"),
    ("nature.com",         "Academic & Research", "https://www.nature.com/robots.txt"),
    ("sciencedirect.com",  "Academic & Research", "https://www.sciencedirect.com/robots.txt"),
    ("ieee.org",           "Academic & Research", "https://www.ieee.org/robots.txt"),
    ("springer.com",       "Academic & Research", "https://link.springer.com/robots.txt"),
    ("researchgate.net",   "Academic & Research", "https://www.researchgate.net/robots.txt"),
    ("jstor.org",          "Academic & Research", "https://www.jstor.org/robots.txt"),
    ("jkuat.ac.ke",        "Academic & Research", "https://www.jkuat.ac.ke/robots.txt"),

    # ── 3. E-commerce & Reviews ───────────────────────────────────────────
    ("amazon.com",         "E-commerce & Reviews", "https://www.amazon.com/robots.txt"),
    ("ebay.com",           "E-commerce & Reviews", "https://www.ebay.com/robots.txt"),
    ("etsy.com",           "E-commerce & Reviews", "https://www.etsy.com/robots.txt"),
    ("walmart.com",        "E-commerce & Reviews", "https://www.walmart.com/robots.txt"),
    ("alibaba.com",        "E-commerce & Reviews", "https://www.alibaba.com/robots.txt"),
    ("tripadvisor.com",    "E-commerce & Reviews", "https://www.tripadvisor.com/robots.txt"),
    ("yelp.com",           "E-commerce & Reviews", "https://www.yelp.com/robots.txt"),
    ("jumia.co.ke",        "E-commerce & Reviews", "https://www.jumia.co.ke/robots.txt"),

    # ── 4. Social & Community ─────────────────────────────────────────────
    ("reddit.com",         "Social & Community", "https://www.reddit.com/robots.txt"),
    ("linkedin.com",       "Social & Community", "https://www.linkedin.com/robots.txt"),
    ("x.com",              "Social & Community", "https://x.com/robots.txt"),
    ("facebook.com",       "Social & Community", "https://www.facebook.com/robots.txt"),
    ("instagram.com",      "Social & Community", "https://www.instagram.com/robots.txt"),
    ("quora.com",          "Social & Community", "https://www.quora.com/robots.txt"),
    ("medium.com",         "Social & Community", "https://medium.com/robots.txt"),
    ("stackoverflow.com",  "Social & Community", "https://stackoverflow.com/robots.txt"),

    # ── 5. Reference & Knowledge ──────────────────────────────────────────
    ("wikipedia.org",      "Reference & Knowledge", "https://en.wikipedia.org/robots.txt"),
    ("britannica.com",     "Reference & Knowledge", "https://www.britannica.com/robots.txt"),
    ("imdb.com",           "Reference & Knowledge", "https://www.imdb.com/robots.txt"),
    ("github.com",         "Reference & Knowledge", "https://github.com/robots.txt"),
    ("w3.org",             "Reference & Knowledge", "https://www.w3.org/robots.txt"),
    ("mozilla.org",        "Reference & Knowledge", "https://www.mozilla.org/robots.txt"),
    ("archive.org",        "Reference & Knowledge", "https://archive.org/robots.txt"),
    ("goodreads.com",      "Reference & Knowledge", "https://www.goodreads.com/robots.txt"),

    # ── 6. Government & Institutional ─────────────────────────────────────
    ("usa.gov",            "Government & Institutional", "https://www.usa.gov/robots.txt"),
    ("europa.eu",          "Government & Institutional", "https://europa.eu/robots.txt"),
    ("gov.uk",             "Government & Institutional", "https://www.gov.uk/robots.txt"),
    ("who.int",            "Government & Institutional", "https://www.who.int/robots.txt"),
    ("un.org",             "Government & Institutional", "https://www.un.org/robots.txt"),
    ("worldbank.org",      "Government & Institutional", "https://www.worldbank.org/robots.txt"),
    ("ecitizen.go.ke",     "Government & Institutional", "https://www.ecitizen.go.ke/robots.txt"),
    ("kenyalaw.org",       "Government & Institutional", "https://www.kenyalaw.org/robots.txt"),
]

assert len(WEBSITES) == 50, f"expected 50 sites, got {len(WEBSITES)}"
