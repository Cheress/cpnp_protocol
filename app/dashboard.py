"""
cpnp/app/dashboard.py
──────────────────────
Week 4 — Supervisor Demo Dashboard.
Served at GET /dashboard
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Week 4 — Dashboard"])

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CPNP — Live Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg:        #0d1117;
  --surface:   #161b22;
  --border:    #30363d;
  --text:      #e6edf3;
  --muted:     #8b949e;
  --green:     #3fb950;
  --red:       #f85149;
  --yellow:    #d29922;
  --blue:      #58a6ff;
  --purple:    #bc8cff;
  --accent:    #238636;
  --mono:      'JetBrains Mono', monospace;
  --sans:      'DM Sans', sans-serif;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: var(--sans); font-size: 14px; min-height: 100vh; }

/* ── Top bar ── */
.topbar {
  background: var(--surface); border-bottom: 1px solid var(--border);
  padding: .75rem 1.5rem; display: flex; align-items: center; gap: 1rem;
  position: sticky; top: 0; z-index: 100;
}
.topbar h1 { font-size: 1rem; font-weight: 700; color: var(--blue); font-family: var(--mono); }
.topbar .sub { color: var(--muted); font-size:.8rem; flex:1; }
.pulse { width:10px; height:10px; border-radius:50%; background:var(--green); animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(1.3)} }
.status-badge { font-family:var(--mono); font-size:.72rem; padding:.2rem .6rem; border-radius:4px; font-weight:600; }
.badge-ok    { background:#1a3a27; color:var(--green); }
.badge-warn  { background:#3a2a00; color:var(--yellow); }
.badge-err   { background:#3a1a1a; color:var(--red); }

/* ── Layout ── */
.grid { display: grid; grid-template-columns: 340px 1fr; gap: 1rem; padding: 1rem; max-width: 1400px; margin: 0 auto; }
.col  { display: flex; flex-direction: column; gap: 1rem; }

/* ── Cards ── */
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.card-head { padding: .65rem 1rem; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap:.5rem; }
.card-head h2 { font-size: .82rem; font-weight: 700; text-transform: uppercase; letter-spacing:.06em; color: var(--muted); flex:1; }
.card-body { padding: 1rem; }

/* ── Stats row ── */
.stats { display: grid; grid-template-columns: repeat(4,1fr); gap: .75rem; margin-bottom: 1rem; }
.stat  { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:.85rem; text-align:center; }
.stat .num  { font-family:var(--mono); font-size:1.8rem; font-weight:700; line-height:1; }
.stat .label{ font-size:.72rem; color:var(--muted); margin-top:.3rem; text-transform:uppercase; letter-spacing:.04em; }
.stat.green .num { color:var(--green); }
.stat.red   .num { color:var(--red); }
.stat.blue  .num { color:var(--blue); }
.stat.yellow .num{ color:var(--yellow); }

/* ── Mono values ── */
.mono  { font-family: var(--mono); font-size: .78rem; }
.kv    { display: flex; justify-content: space-between; align-items: flex-start; padding: .35rem 0; border-bottom: 1px solid var(--border); gap:.5rem; }
.kv:last-child { border-bottom: none; }
.kv .k { color: var(--muted); font-size: .78rem; flex-shrink:0; }
.kv .v { font-family: var(--mono); font-size: .78rem; color: var(--text); text-align:right; word-break:break-all; }
.kv .v.green { color: var(--green); }
.kv .v.red   { color: var(--red); }
.kv .v.blue  { color: var(--blue); }

/* ── Purpose tags ── */
.tags { display:flex; flex-wrap:wrap; gap:.3rem; margin-top:.3rem; }
.tag  { font-size:.7rem; font-family:var(--mono); padding:.15rem .5rem; border-radius:3px; border:1px solid var(--border); color:var(--muted); }
.tag.active { border-color:var(--blue); color:var(--blue); background:#0d2044; }

/* ── Controls ── */
.btn { display:inline-flex; align-items:center; gap:.4rem; padding:.5rem 1rem; border-radius:6px; border:1px solid var(--border); background:var(--surface); color:var(--text); font-family:var(--sans); font-size:.82rem; cursor:pointer; transition:all .15s; font-weight:500; }
.btn:hover  { border-color:var(--blue); color:var(--blue); }
.btn.green  { background:var(--accent); border-color:var(--accent); color:#fff; }
.btn.green:hover { background:#2ea043; }
.btn.red    { background:#b62324; border-color:#b62324; color:#fff; }
.btn.red:hover   { background:#d73a3a; }
.btn.yellow { background:#9e6a03; border-color:#9e6a03; color:#fff; }
.btn.yellow:hover{ background:#bf8700; }
.btns { display:flex; flex-wrap:wrap; gap:.4rem; }

input[type=range]  { width:100%; accent-color:var(--blue); cursor:pointer; }
input[type=number],select { background:var(--bg); border:1px solid var(--border); border-radius:5px; color:var(--text); padding:.35rem .6rem; font-size:.82rem; font-family:var(--mono); width:100%; }

/* ── Audit log table ── */
.log-wrap { max-height: 420px; overflow-y: auto; }
.log-wrap::-webkit-scrollbar { width:5px; }
.log-wrap::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }
table.log { width:100%; border-collapse:collapse; font-family:var(--mono); font-size:.72rem; }
table.log th { padding:.4rem .6rem; color:var(--muted); text-align:left; border-bottom:1px solid var(--border); position:sticky;top:0;background:var(--surface);z-index:1; }
table.log td { padding:.35rem .6rem; border-bottom:1px solid #1c2128; vertical-align:middle; }
table.log tr:hover td { background:#1c2128; }
.verdict-chip { display:inline-block; padding:.1rem .45rem; border-radius:3px; font-size:.68rem; font-weight:600; white-space:nowrap; }
.v-compliant { background:#1a3a27; color:var(--green); }
.v-blocked   { background:#3a1a1a; color:var(--red); }
.v-no-token  { background:#2a1a0a; color:var(--yellow); }

/* ── Session list ── */
.session-item { padding:.5rem 0; border-bottom:1px solid var(--border); display:flex; align-items:center; gap:.5rem; }
.session-item:last-child { border-bottom:none; }
.sess-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
.s-agreed   { background:var(--green); }
.s-rejected { background:var(--red); }
.s-countered{ background:var(--yellow); }
.s-init     { background:var(--muted); }
.sess-info  { flex:1; min-width:0; }
.sess-op    { font-size:.78rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sess-meta  { font-size:.68rem; color:var(--muted); font-family:var(--mono); }

/* ── Progress bar ── */
.pbar-wrap { background:#1c2128; border-radius:4px; height:8px; overflow:hidden; margin-top:.5rem; }
.pbar      { height:100%; border-radius:4px; transition:width .5s ease; }
.pbar.green { background:var(--green); }
.pbar.red   { background:var(--red); }

/* ── Flash animation for new rows ── */
@keyframes flashIn { from{background:#0d2044} to{background:transparent} }
.new-row td { animation: flashIn .8s ease-out; }

/* ── Scrollbar style ── */
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }

/* ── Responsive ── */
@media(max-width:900px){
  .grid{grid-template-columns:1fr;}
  .stats{grid-template-columns:repeat(2,1fr);}
}
</style>
</head>
<body>

<!-- Top bar -->
<div class="topbar">
  <div class="pulse" id="pulse"></div>
  <h1>⚡ CPNP Live Dashboard</h1>
  <span class="sub">Crawl Policy Negotiation Protocol — Supervisor Demo</span>
  <span class="status-badge badge-ok" id="conn-badge">● LIVE</span>
  <span class="mono" style="color:var(--muted);font-size:.72rem" id="last-update">—</span>
</div>

<!-- Stats row -->
<div style="padding:1rem 1rem 0;max-width:1400px;margin:0 auto">
  <div class="stats">
    <div class="stat green"><div class="num" id="s-total">—</div><div class="label">Total Requests</div></div>
    <div class="stat blue"><div class="num" id="s-compliant">—</div><div class="label">Compliant</div></div>
    <div class="stat red"><div class="num" id="s-blocked">—</div><div class="label">Blocked</div></div>
    <div class="stat yellow"><div class="num" id="s-rate">—%</div><div class="label">Compliance Rate</div></div>
  </div>
</div>

<!-- Main grid -->
<div class="grid">

  <!-- LEFT COLUMN -->
  <div class="col">

    <!-- Server Identity -->
    <div class="card">
      <div class="card-head"><h2>🔑 Server Identity</h2></div>
      <div class="card-body">
        <div class="kv"><span class="k">Server DID</span><span class="v blue mono" id="server-did">loading…</span></div>
        <div class="kv"><span class="k">CA DID</span><span class="v mono" id="ca-did">loading…</span></div>
        <div class="kv"><span class="k">VCs Issued</span><span class="v green" id="vc-count">—</span></div>
        <div class="kv"><span class="k">DIDs Registered</span><span class="v" id="did-count">—</span></div>
        <div class="kv"><span class="k">Sessions</span><span class="v" id="sess-count">—</span></div>
      </div>
    </div>

    <!-- Server Policy -->
    <div class="card">
      <div class="card-head"><h2>📋 Server Policy</h2><span class="status-badge badge-ok" id="cred-badge">VC REQUIRED</span></div>
      <div class="card-body">
        <div class="kv"><span class="k">Max Crawl Rate</span><span class="v green" id="pol-rate">— req/min</span></div>
        <div class="kv"><span class="k">Allowed Paths</span><span class="v mono" id="pol-paths">—</span></div>
        <div class="kv"><span class="k">Blocked Paths</span><span class="v red mono" id="pol-blocked">—</span></div>
        <div class="kv"><span class="k">Purposes</span><span class="v" style="text-align:right"><div class="tags" id="pol-purposes"></div></span></div>
      </div>
    </div>

    <!-- Change Policy -->
    <div class="card">
      <div class="card-head"><h2>⚙️ Change Policy <span style="color:var(--yellow);font-size:.7rem;font-weight:400">(live — no restart)</span></h2></div>
      <div class="card-body" style="display:flex;flex-direction:column;gap:.75rem">
        <div>
          <label style="font-size:.75rem;color:var(--muted);display:block;margin-bottom:.3rem">Max Crawl Rate: <span id="rate-display" style="color:var(--blue)">30</span> req/min</label>
          <input type="range" id="rate-slider" min="5" max="120" value="30"
            oninput="document.getElementById('rate-display').textContent=this.value">
        </div>
        <div>
          <label style="font-size:.75rem;color:var(--muted);display:block;margin-bottom:.3rem">Allowed Purposes</label>
          <select id="purpose-select" multiple style="height:90px">
            <option value="ResearchCrawler" selected>ResearchCrawler</option>
            <option value="SearchIndexer" selected>SearchIndexer</option>
            <option value="ArchiveCrawler" selected>ArchiveCrawler</option>
            <option value="SecurityAuditor">SecurityAuditor</option>
            <option value="AITrainer">AITrainer</option>
          </select>
        </div>
        <div>
          <label style="font-size:.75rem;color:var(--muted);display:block;margin-bottom:.3rem">Allowed Paths (comma-separated)</label>
          <input type="text" id="paths-input" value="/,/blog,/docs,/research"
            style="background:var(--bg);border:1px solid var(--border);border-radius:5px;color:var(--text);padding:.35rem .6rem;font-size:.82rem;font-family:var(--mono);width:100%">
        </div>
        <div style="display:flex;align-items:center;gap:.5rem">
          <input type="checkbox" id="cred-toggle" checked style="width:16px;height:16px;cursor:pointer">
          <label for="cred-toggle" style="font-size:.82rem;cursor:pointer">Require Verifiable Credential</label>
        </div>
        <button class="btn yellow" onclick="applyPolicy()">⚡ Apply Policy Changes</button>
        <div id="policy-msg" style="font-size:.75rem;color:var(--green);min-height:1rem"></div>
      </div>
    </div>

    <!-- Active Sessions -->
    <div class="card">
      <div class="card-head"><h2>🔄 Active Sessions</h2></div>
      <div class="card-body" style="max-height:220px;overflow-y:auto" id="session-list">
        <span style="color:var(--muted);font-size:.8rem">No sessions yet</span>
      </div>
    </div>

  </div><!-- /left col -->

  <!-- RIGHT COLUMN -->
  <div class="col">

    <!-- Demo Controls -->
    <div class="card">
      <div class="card-head"><h2>🚀 Demo Controls <span style="color:var(--muted);font-size:.7rem;font-weight:400">— click to fire crawl events</span></h2></div>
      <div class="card-body">
        <div class="btns">
          <button class="btn green" onclick="demoCrawl('compliant','/site/blog')">✅ Compliant Crawl (blog)</button>
          <button class="btn green" onclick="demoCrawl('compliant','/site/research')">✅ Compliant Crawl (research)</button>
          <button class="btn red"   onclick="demoCrawl('no_token','/site/blog')">❌ No Token</button>
          <button class="btn red"   onclick="demoCrawl('forged','/site/blog')">❌ Forged JWT</button>
          <button class="btn red"   onclick="demoCrawl('path_violation','/site/admin')">❌ Path Violation (/admin)</button>
          <button class="btn yellow" onclick="demoBurst()">💥 Adversarial Burst (5 attacks)</button>
          <button class="btn" onclick="clearSessions()">🗑 Clear Sessions</button>
        </div>
        <div id="demo-msg" style="font-size:.75rem;color:var(--green);margin-top:.5rem;min-height:1rem"></div>
      </div>
    </div>

    <!-- Verdict breakdown -->
    <div class="card">
      <div class="card-head"><h2>📊 Verdict Breakdown</h2></div>
      <div class="card-body" id="verdict-breakdown">
        <span style="color:var(--muted);font-size:.8rem">Waiting for traffic…</span>
      </div>
    </div>

    <!-- Live Audit Log -->
    <div class="card" style="flex:1">
      <div class="card-head">
        <h2>📜 Live Audit Log</h2>
        <span style="color:var(--muted);font-size:.72rem;font-family:var(--mono)" id="log-count">0 entries</span>
        <label style="display:flex;align-items:center;gap:.3rem;font-size:.75rem;cursor:pointer;margin-left:.5rem">
          <input type="checkbox" id="auto-scroll" checked> auto-scroll
        </label>
      </div>
      <div class="log-wrap" id="log-wrap">
        <table class="log">
          <thead><tr>
            <th>Time</th>
            <th>Crawler</th>
            <th>Path</th>
            <th>Verdict</th>
            <th>Purpose</th>
            <th>Detail</th>
          </tr></thead>
          <tbody id="log-body">
            <tr><td colspan="6" style="color:var(--muted);text-align:center;padding:2rem">Waiting for crawl traffic…</td></tr>
          </tbody>
        </table>
      </div>
    </div>

  </div><!-- /right col -->
</div><!-- /grid -->

<script>
const BASE = "";
let prevEventCount = 0;
let prevSessions   = {};

// ── Polling ───────────────────────────────────────────────────────────────────
async function poll() {
  try {
    const r = await fetch(`${BASE}/status`);
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    update(d);
    document.getElementById("conn-badge").textContent = "● LIVE";
    document.getElementById("conn-badge").className = "status-badge badge-ok";
    document.getElementById("last-update").textContent = new Date().toLocaleTimeString();
    document.getElementById("pulse").style.background = "var(--green)";
  } catch(e) {
    document.getElementById("conn-badge").textContent = "● OFFLINE";
    document.getElementById("conn-badge").className = "status-badge badge-err";
    document.getElementById("pulse").style.background = "var(--red)";
  }
}

// ── Update UI ─────────────────────────────────────────────────────────────────
function update(d) {
  // Stats
  const a = d.audit;
  document.getElementById("s-total").textContent    = a.total_requests;
  document.getElementById("s-compliant").textContent= a.compliant;
  document.getElementById("s-blocked").textContent  = a.blocked;
  document.getElementById("s-rate").textContent     = a.compliance_rate + "%";

  // Server identity
  document.getElementById("server-did").textContent  = d.server.did_short;
  document.getElementById("ca-did").textContent      = d.server.ca_did;
  document.getElementById("vc-count").textContent    = d.server.credentials_issued;
  document.getElementById("did-count").textContent   = d.server.registered_dids;
  document.getElementById("sess-count").textContent  =
    `${d.sessions.agreed} agreed / ${d.sessions.rejected} rejected / ${d.sessions.countered} countering`;

  // Policy panel
  const p = d.policy;
  document.getElementById("pol-rate").textContent    = p.max_crawl_rate + " req/min";
  document.getElementById("pol-paths").textContent   = p.allowed_paths.join(", ");
  document.getElementById("pol-blocked").textContent = p.disallowed_paths.join(", ");
  document.getElementById("cred-badge").textContent  = p.requires_credential ? "VC REQUIRED" : "OPEN";
  document.getElementById("cred-badge").className    = "status-badge " + (p.requires_credential ? "badge-warn" : "badge-ok");

  const allPurposes = ["ResearchCrawler","SearchIndexer","ArchiveCrawler","SecurityAuditor","AITrainer"];
  const purposeDiv = document.getElementById("pol-purposes");
  purposeDiv.innerHTML = allPurposes.map(pu =>
    `<span class="tag ${p.allowed_purposes.includes(pu)?"active":""}">${pu}</span>`
  ).join("");

  // Verdict breakdown
  const vb = document.getElementById("verdict-breakdown");
  const bv = a.by_verdict || {};
  if (Object.keys(bv).length === 0) {
    vb.innerHTML = `<span style="color:var(--muted);font-size:.8rem">No traffic yet</span>`;
  } else {
    const total = a.total_requests || 1;
    vb.innerHTML = Object.entries(bv).map(([verdict,count]) => {
      const pct   = Math.round(count/total*100);
      const cls   = verdict==="COMPLIANT" ? "green" : "red";
      const label = verdict==="COMPLIANT" ? "✅" : "❌";
      return `<div style="margin-bottom:.6rem">
        <div style="display:flex;justify-content:space-between;margin-bottom:.2rem">
          <span style="font-size:.75rem">${label} ${verdict}</span>
          <span style="font-family:var(--mono);font-size:.75rem;color:var(--muted)">${count} (${pct}%)</span>
        </div>
        <div class="pbar-wrap"><div class="pbar ${cls}" style="width:${pct}%"></div></div>
      </div>`;
    }).join("");
  }

  // Active sessions
  const sl = document.getElementById("session-list");
  const acts = d.active_sessions || [];
  if (acts.length === 0) {
    sl.innerHTML = `<span style="color:var(--muted);font-size:.8rem">No sessions yet</span>`;
  } else {
    sl.innerHTML = acts.slice().reverse().map(s => {
      const dotCls = {AGREED:"s-agreed",REJECTED:"s-rejected",COUNTERED:"s-countered",INIT:"s-init"}[s.status]||"s-init";
      return `<div class="session-item">
        <div class="sess-dot ${dotCls}"></div>
        <div class="sess-info">
          <div class="sess-op">${s.operator}</div>
          <div class="sess-meta">${s.status} · r${s.round} · ${s.purpose} · ${s.session_id}</div>
        </div>
        ${s.has_token ? '<span class="status-badge badge-ok" style="font-size:.65rem">JWT</span>' : ''}
      </div>`;
    }).join("");
  }

  // Audit log
  const events = d.recent_events || [];
  if (events.length !== prevEventCount) {
    const newCount = events.length - prevEventCount;
    prevEventCount = events.length;
    document.getElementById("log-count").textContent = events.length + " entries";
    const tbody = document.getElementById("log-body");
    if (events.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="color:var(--muted);text-align:center;padding:2rem">Waiting for crawl traffic…</td></tr>`;
    } else {
      tbody.innerHTML = events.map((e, i) => {
        const isNew = i < newCount;
        const vc = e.verdict === "COMPLIANT" ? "v-compliant" : (e.verdict.includes("NO_TOKEN") ? "v-no-token" : "v-blocked");
        const ts  = (e.timestamp || "").substring(11,19);
        const did = (e.crawler_did || "unknown").substring(8,26)+"…";
        const path= e.path || "/";
        const det = (e.violation_detail || "").substring(0,40) || "—";
        const pur = e.purpose || "—";
        return `<tr class="${isNew?"new-row":""}">
          <td style="color:var(--muted)">${ts}</td>
          <td class="mono" title="${e.crawler_did}">${did}</td>
          <td class="mono">${path}</td>
          <td><span class="verdict-chip ${vc}">${e.verdict}</span></td>
          <td style="color:var(--muted)">${pur}</td>
          <td style="color:var(--muted);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${e.violation_detail||''}">${det}</td>
        </tr>`;
      }).join("");
      if (document.getElementById("auto-scroll").checked) {
        const wrap = document.getElementById("log-wrap");
        wrap.scrollTop = 0;
      }
    }
  }
}

// ── Demo actions ──────────────────────────────────────────────────────────────
async function demoCrawl(mode, path="/site/blog") {
  const r = await fetch(`${BASE}/demo/crawl`, {method:"POST",
    headers:{"Content-Type":"application/json"},body:JSON.stringify({mode,target_path:path})});
  const d = await r.json();
  const icons = {COMPLIANT:"✅",BLOCKED_NO_TOKEN:"🚫",BLOCKED_FORGED:"🔴",BLOCKED_PATH_VIOLATION:"⛔"};
  const icon = icons[d.verdict] || "❓";
  document.getElementById("demo-msg").textContent = `${icon} ${d.verdict} (${d.status}) — ${mode} · ${path}`;
  setTimeout(poll, 300);
}

async function demoBurst() {
  document.getElementById("demo-msg").textContent = "💥 Launching adversarial burst…";
  const attacks = [
    ["no_token","/site/blog"],["forged","/site/blog"],
    ["path_violation","/site/admin"],["no_token","/site/research"],
    ["forged","/site/"]
  ];
  for (const [mode,path] of attacks) {
    await demoCrawl(mode,path);
    await new Promise(r=>setTimeout(r,400));
  }
  document.getElementById("demo-msg").textContent = "💥 Adversarial burst complete — check audit log";
}

async function applyPolicy() {
  const rate = parseInt(document.getElementById("rate-slider").value);
  const sel  = document.getElementById("purpose-select");
  const purposes = Array.from(sel.selectedOptions).map(o=>o.value);
  const paths= document.getElementById("paths-input").value.split(",").map(s=>s.trim()).filter(Boolean);
  const cred = document.getElementById("cred-toggle").checked;
  const r = await fetch(`${BASE}/cpnp/policy/update`,{method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({allowed_purposes:purposes,max_crawl_rate:rate,allowed_paths:paths,requires_credential:cred})});
  const d = await r.json();
  document.getElementById("policy-msg").textContent = "✅ " + (d.message||"Policy updated");
  setTimeout(()=>{document.getElementById("policy-msg").textContent="";},3000);
  poll();
}

async function clearSessions() {
  await fetch(`${BASE}/cpnp/sessions`,{method:"DELETE"});
  prevSessions={};
  document.getElementById("demo-msg").textContent="🗑 Sessions cleared";
  poll();
}

// ── Boot ─────────────────────────────────────────────────────────────────────
poll();
setInterval(poll, 2000);
</script>
</body>
</html>"""

@router.get("/dashboard", response_class=HTMLResponse,
            summary="Supervisor Demo Dashboard — live CPNP monitor")
def dashboard():
    """
    The Week 4 supervisor demo dashboard.
    Polls /status every 2 seconds and renders live state.
    """
    return HTMLResponse(DASHBOARD_HTML)
