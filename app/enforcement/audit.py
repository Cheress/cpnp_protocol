from __future__ import annotations
import json, sqlite3, os
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional

DB_PATH = os.environ.get("CPNP_DB","cpnp_audit.db")

@dataclass
class CrawlRequestLog:
    crawler_did: str; token_id: str; method: str; url: str; path: str
    status_code: int; verdict: str; violation_detail: str = ""
    agreed_rate: int = 0; agreed_paths: list = None; purpose: str = ""
    def __post_init__(self):
        if self.agreed_paths is None: self.agreed_paths=[]

class AuditLog:
    def __init__(self,db_path=DB_PATH):
        self.db_path=db_path
        self._conn=sqlite3.connect(db_path,check_same_thread=False)
        self._conn.row_factory=sqlite3.Row; self._bootstrap()
    def _bootstrap(self):
        self._conn.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS crawl_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
                crawler_did TEXT NOT NULL DEFAULT 'unknown', token_id TEXT NOT NULL DEFAULT '',
                method TEXT NOT NULL DEFAULT 'GET', url TEXT NOT NULL, path TEXT NOT NULL,
                status_code INTEGER NOT NULL, verdict TEXT NOT NULL,
                violation_detail TEXT NOT NULL DEFAULT '', agreed_rate INTEGER NOT NULL DEFAULT 0,
                agreed_paths TEXT NOT NULL DEFAULT '[]', purpose TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS negotiation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL, event_type TEXT NOT NULL,
                crawler_did TEXT NOT NULL DEFAULT '', operator_name TEXT NOT NULL DEFAULT '',
                detail TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_crawl_crawler ON crawl_requests(crawler_did);
            CREATE INDEX IF NOT EXISTS idx_crawl_verdict ON crawl_requests(verdict);
            CREATE INDEX IF NOT EXISTS idx_crawl_ts ON crawl_requests(timestamp);
        """); self._conn.commit()
    def record_request(self,entry: CrawlRequestLog):
        now=datetime.now(timezone.utc).isoformat()
        self._conn.execute("INSERT INTO crawl_requests (timestamp,crawler_did,token_id,method,url,path,status_code,verdict,violation_detail,agreed_rate,agreed_paths,purpose) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (now,entry.crawler_did,entry.token_id,entry.method,entry.url,entry.path,entry.status_code,entry.verdict,entry.violation_detail,entry.agreed_rate,json.dumps(entry.agreed_paths),entry.purpose))
        self._conn.commit()
    def record_negotiation(self,session_id,event_type,crawler_did="",operator_name="",detail=None):
        now=datetime.now(timezone.utc).isoformat()
        self._conn.execute("INSERT INTO negotiation_events (timestamp,session_id,event_type,crawler_did,operator_name,detail) VALUES (?,?,?,?,?,?)",
            (now,session_id,event_type,crawler_did,operator_name,json.dumps(detail or {})))
        self._conn.commit()
    def summary(self):
        cur=self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM crawl_requests"); total=cur.fetchone()[0]
        cur.execute("SELECT verdict,COUNT(*) c FROM crawl_requests GROUP BY verdict ORDER BY c DESC")
        by_verdict={r["verdict"]:r["c"] for r in cur.fetchall()}
        compliant=by_verdict.get("COMPLIANT",0)
        rate=round(compliant/total*100,1) if total else 0.0
        cur.execute("SELECT crawler_did,COUNT(*) total,SUM(CASE WHEN verdict='COMPLIANT' THEN 1 ELSE 0 END) ok,SUM(CASE WHEN verdict!='COMPLIANT' THEN 1 ELSE 0 END) blocked FROM crawl_requests GROUP BY crawler_did ORDER BY blocked DESC LIMIT 10")
        crawlers=[dict(r) for r in cur.fetchall()]
        cur.execute("SELECT COUNT(DISTINCT session_id) FROM negotiation_events"); sessions=cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM negotiation_events WHERE event_type='AGREED'"); agreed=cur.fetchone()[0]
        return {"total_requests":total,"compliant_requests":compliant,"blocked_requests":total-compliant,
                "compliance_rate_pct":rate,"by_verdict":by_verdict,"crawler_breakdown":crawlers,
                "total_sessions":sessions,"agreed_sessions":agreed}
    def recent_events(self,limit=50):
        cur=self._conn.cursor()
        cur.execute("SELECT timestamp,crawler_did,url,path,verdict,violation_detail,status_code,purpose,agreed_rate FROM crawl_requests ORDER BY timestamp DESC LIMIT ?",(limit,))
        return [dict(r) for r in cur.fetchall()]
    def blocked_requests(self,limit=50):
        cur=self._conn.cursor()
        cur.execute("SELECT timestamp,crawler_did,url,verdict,violation_detail,status_code FROM crawl_requests WHERE verdict!='COMPLIANT' ORDER BY timestamp DESC LIMIT ?",(limit,))
        return [dict(r) for r in cur.fetchall()]
    def compliant_requests(self,limit=50):
        cur=self._conn.cursor()
        cur.execute("SELECT timestamp,crawler_did,url,path,purpose,agreed_rate FROM crawl_requests WHERE verdict='COMPLIANT' ORDER BY timestamp DESC LIMIT ?",(limit,))
        return [dict(r) for r in cur.fetchall()]
    def compliance_report(self,crawler_did):
        cur=self._conn.cursor()
        cur.execute("SELECT COUNT(*) total,SUM(CASE WHEN verdict='COMPLIANT' THEN 1 ELSE 0 END) ok,SUM(CASE WHEN verdict!='COMPLIANT' THEN 1 ELSE 0 END) blocked,MIN(timestamp) first_seen,MAX(timestamp) last_seen FROM crawl_requests WHERE crawler_did=?",(crawler_did,))
        row=dict(cur.fetchone()); total=row.get("total") or 0; ok=row.get("ok") or 0
        cur.execute("SELECT verdict,violation_detail,url,timestamp FROM crawl_requests WHERE crawler_did=? AND verdict!='COMPLIANT' ORDER BY timestamp DESC LIMIT 20",(crawler_did,))
        violations=[dict(r) for r in cur.fetchall()]
        return {"crawler_did":crawler_did,"total_requests":total,"compliant":ok,"blocked":total-ok,
                "compliance_rate":f"{round(ok/total*100,1) if total else 0}%",
                "first_seen":row.get("first_seen"),"last_seen":row.get("last_seen"),"recent_violations":violations}
    def path_violations(self):
        cur=self._conn.cursor()
        cur.execute("SELECT path,crawler_did,COUNT(*) attempts,MAX(timestamp) last_attempt FROM crawl_requests WHERE verdict='BLOCKED_PATH_VIOLATION' GROUP BY path,crawler_did ORDER BY attempts DESC")
        return [dict(r) for r in cur.fetchall()]
    def export_sql_queries(self):
        return f"""-- CPNP Audit SQL Queries — db: {self.db_path} (sqlitebrowser.org)
-- 1. Compliance summary
SELECT verdict,COUNT(*) count,ROUND(COUNT(*)*100.0/(SELECT COUNT(*) FROM crawl_requests),1) pct FROM crawl_requests GROUP BY verdict ORDER BY count DESC;
-- 2. Per-crawler compliance_pct
SELECT crawler_did,COUNT(*) total,SUM(CASE WHEN verdict='COMPLIANT' THEN 1 ELSE 0 END) compliant,ROUND(SUM(CASE WHEN verdict='COMPLIANT' THEN 1.0 ELSE 0 END)/COUNT(*)*100,1) compliance_pct FROM crawl_requests GROUP BY crawler_did ORDER BY compliance_pct ASC;
-- 3. Blocked requests
SELECT timestamp,crawler_did,url,verdict,violation_detail FROM crawl_requests WHERE verdict!='COMPLIANT' ORDER BY timestamp DESC LIMIT 100;
-- 4. BLOCKED_PATH_VIOLATION paths
SELECT path,crawler_did,COUNT(*) attempts FROM crawl_requests WHERE verdict='BLOCKED_PATH_VIOLATION' GROUP BY path,crawler_did ORDER BY attempts DESC;
-- 5. Hourly activity
SELECT strftime('%Y-%m-%dT%H:00Z',timestamp) hour,COUNT(*) total FROM crawl_requests GROUP BY hour ORDER BY hour DESC LIMIT 24;
-- 6. By crawler (replace DID)
SELECT timestamp,method,url,verdict,status_code FROM crawl_requests WHERE crawler_did='REPLACE_WITH_CRAWLER_DID' ORDER BY timestamp DESC;
-- 7. Token usage
SELECT timestamp,url,path,verdict FROM crawl_requests WHERE token_id='REPLACE_WITH_TOKEN_ID' ORDER BY timestamp ASC;
-- 8. Negotiation events
SELECT timestamp,session_id,event_type,crawler_did,operator_name FROM negotiation_events ORDER BY timestamp DESC LIMIT 50;
-- 9. Session outcomes
SELECT event_type,COUNT(*) count FROM negotiation_events WHERE event_type IN ('AGREED','REJECTED') GROUP BY event_type;
-- 10. No-token bypass attempts
SELECT DISTINCT crawler_did,COUNT(*) attempts FROM crawl_requests WHERE verdict='BLOCKED_NO_TOKEN' GROUP BY crawler_did ORDER BY attempts DESC;"""
    def close(self): self._conn.close()
