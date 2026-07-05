# Crawler Policy-Fidelity Benchmark — Runbook

This benchmark compares how faithfully real crawl frameworks (Scrapy, Apache
Nutch, Heritrix) respect a published policy, and demonstrates that CPNP
enforcement guarantees fidelity even when a crawler ignores robots.txt.

**Run this on your own machine** (it needs to bind a local port and install
crawlers). The harness itself needs only Python 3; the crawlers need their own
runtimes.

---

## The experiment in one sentence

Point each crawler at a controlled server that publishes a known robots.txt and
a known CPNP policy, run once with the server in **robots mode** (advisory only)
and once in **cpnp mode** (enforced), and measure coverage, politeness, and
policy-fidelity in each case.

---

## Metrics (state these definitions in the thesis)

- **Coverage** = allowed pages fetched / total allowed pages. Higher is better.
- **Politeness** = 1 − (fraction of 60-second windows exceeding the rate limit). Higher is better.
- **Policy-Fidelity** = 1 − (forbidden pages accessed / total forbidden pages). Higher is better.

The corpus has 20 allowed pages, 10 forbidden pages (declared `Disallow` in
robots.txt), and a 30 req/min declared limit. Ground truth is fixed and known,
so all three metrics are computed exactly.

---

## Step 0 — Start the test server

Terminal 1, robots mode (advisory):
```bash
cd benchmarks
python3 server/test_server.py --port 8080 --mode robots
```

For the enforced run, restart it in cpnp mode:
```bash
python3 server/test_server.py --port 8080 --mode cpnp
```

The server resets its log on each start, so run one crawler per server start,
then compute metrics before restarting.

---

## Step 1 — Naive baseline (the control)

```bash
# robots mode: crawler ignores robots.txt, server can't stop it
python3 crawlers/naive_crawler.py --base http://localhost:8080
python3 metrics/compute_metrics.py --label "Naive (robots)" --mode robots

# cpnp mode: SAME crawler, but forbidden fetches are blocked
#   (restart server in cpnp mode first)
python3 crawlers/naive_crawler.py --base http://localhost:8080
python3 metrics/compute_metrics.py --label "Naive (cpnp)" --mode cpnp
```

Expected: fidelity 0.0 in robots mode, 1.0 in cpnp mode. This is the headline.

---

## Step 2 — Scrapy

Install:
```bash
pip install scrapy
```

Run (obeys robots.txt by default):
```bash
# restart server in robots mode first
scrapy runspider crawlers/scrapy_crawler.py -a base=http://localhost:8080
python3 metrics/compute_metrics.py --label "Scrapy (obey)" --mode robots

# disobedient run — proves robots.txt is optional
scrapy runspider crawlers/scrapy_crawler.py -a base=http://localhost:8080 -a obey=false
python3 metrics/compute_metrics.py --label "Scrapy (ignore)" --mode robots

# CPNP-enforced run — restart server in cpnp mode
scrapy runspider crawlers/scrapy_crawler.py -a base=http://localhost:8080 -a obey=false
python3 metrics/compute_metrics.py --label "Scrapy (cpnp)" --mode cpnp
```

---

## Step 3 — Apache Nutch

Nutch is Java/Hadoop-based. Easiest via Docker:
```bash
docker run -it apache/nutch bash
```
Or install locally (requires Java 11+):
```bash
wget https://archive.apache.org/dist/nutch/1.20/apache-nutch-1.20-bin.tar.gz
tar xzf apache-nutch-1.20-bin.tar.gz
cd apache-nutch-1.20
```

Configure `conf/nutch-site.xml` to set `http.agent.name` and point the seed
list at `http://localhost:8080/`. Set `http.robots.rules` handling as needed.
Inject and crawl:
```bash
echo "http://localhost:8080/" > urls/seed.txt
bin/nutch inject crawldb urls
bin/nutch generate crawldb segments
bin/nutch fetch segments/*
```
Then:
```bash
python3 metrics/compute_metrics.py --label "Nutch" --mode robots
```
(The server log records what Nutch fetched; the metrics read that log.)

---

## Step 4 — Heritrix

Heritrix is the Internet Archive's Java crawler. Via Docker:
```bash
docker run -p 8443:8443 iipc/heritrix
```
Access the web UI at `https://localhost:8443` (default admin/admin). Create a
job with seed `http://localhost:8080/`, configure the crawl scope, and launch.
Heritrix respects robots.txt by default; toggle
`metadata.robotsPolicyName` to `ignore` for the disobedient run.

Then:
```bash
python3 metrics/compute_metrics.py --label "Heritrix" --mode robots
```

---

## Step 5 — The comparison table

After all runs:
```bash
python3 metrics/compute_metrics.py --report
```

Produces the final table (also in `results/benchmark_results.csv`):

