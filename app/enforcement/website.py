from fastapi import APIRouter
from fastapi.responses import HTMLResponse
router = APIRouter(prefix="/site",tags=["Test Website"])
def _page(title,body,color="#2E75B6"):
    return HTMLResponse(f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>CPNP — {title}</title>
<style>body{{font-family:Georgia,serif;max-width:780px;margin:3rem auto;padding:0 2rem;background:#f9f9f7}}
h1{{color:{color};border-bottom:3px solid {color};padding-bottom:.4rem}}
nav{{background:{color};padding:.8rem 1.2rem;border-radius:6px;margin-bottom:2rem}}
nav a{{color:#fff;margin-right:1.2rem;text-decoration:none;font-weight:bold}}
.card{{background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:1.4rem;margin:1rem 0;box-shadow:0 2px 4px rgba(0,0,0,.06)}}
.badge{{background:{color};color:#fff;padding:.25rem .7rem;border-radius:14px;font-size:.8rem}}
table{{width:100%;border-collapse:collapse}}td,th{{border:1px solid #ddd;padding:6px 10px;text-align:left}}
th{{background:#eee}}footer{{color:#999;font-size:.8rem;margin-top:3rem;border-top:1px solid #ddd;padding-top:.8rem}}</style>
</head><body>
<nav><a href="/site/">🏠 Home</a><a href="/site/blog">📝 Blog</a><a href="/site/research">🔬 Research</a><a href="/site/admin">⚙️ Admin</a></nav>
<h1>{title}</h1>{body}
<footer>CPNP Test Website · <a href="/docs">API Docs</a> · <a href="/dashboard">📊 Dashboard</a> · <a href="/audit/summary">Audit Log</a></footer>
</body></html>""")
@router.get("/",summary="Home page")
def site_home():
    return _page("Home","""<div class="card"><p><span class="badge">CPNP Protected</span></p>
<p>Every request requires a valid <code>CPNP-Token</code> header. Requests without a token, with forged tokens, or accessing disallowed paths are blocked with HTTP 451.</p></div>
<div class="card"><h3>Pages on this site</h3><ul><li><a href="/site/">/</a> — Home</li><li><a href="/site/blog">/blog</a> — Blog</li><li><a href="/site/research">/research</a> — Research data</li><li><a href="/site/admin">/admin</a> — Admin (always blocked)</li></ul></div>""")
@router.get("/blog",summary="Blog page")
def site_blog():
    return _page("Blog","""<div class="card"><h3>The End of robots.txt</h3><p>For thirty years, robots.txt was the primary crawl governance mechanism. CPNP proposes a cryptographically verifiable, negotiated replacement.</p><p><span class="badge">Research</span></p></div>
<div class="card"><h3>Consent in the Age of AI</h3><p>Longpre et al. (2024) audited 14,000 web domains and found rapid escalation of data restrictions — a protocol failure, not a content problem.</p><p><span class="badge">Research</span></p></div>""",color="#217346")
@router.get("/research",summary="Research data page")
def site_research():
    return _page("Research Data","""<div class="card"><p><span class="badge">ResearchCrawler only</span></p><p>Structured research data. Access restricted to crawlers with a ResearchCrawler Verifiable Credential.</p></div>
<div class="card"><h3>Pilot Negotiation Logs</h3><table><tr><th>Session</th><th>Rounds</th><th>Outcome</th><th>Purpose</th></tr>
<tr><td>sess-001</td><td>1</td><td>AGREED</td><td>ResearchCrawler</td></tr>
<tr><td>sess-002</td><td>2</td><td>AGREED</td><td>SearchIndexer</td></tr>
<tr><td>sess-003</td><td>1</td><td>REJECTED</td><td>AITrainer</td></tr></table></div>""",color="#7B3F00")
@router.get("/admin",summary="Admin panel (always blocked)")
def site_admin():
    return _page("Admin Panel","<div class='card'><p>You should never reach this page via a compliant crawler. If you see this, enforcement middleware is not working.</p></div>",color="#C00000")
