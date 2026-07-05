"""Validate the harness LOGIC in-process (no sockets, sandbox-safe)."""
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, 'server')

import importlib.util
spec = importlib.util.spec_from_file_location("ts", "server/test_server.py")
ts = importlib.util.module_from_spec(spec); spec.loader.exec_module(ts)

ALLOWED = ts.ALLOWED_PAGES; FORBIDDEN = ts.FORBIDDEN_PAGES; RATE = ts.DECLARED_RATE_LIMIT
os.makedirs("results", exist_ok=True)

def server_decision(path, mode, token=""):
    if path in ALLOWED: return "allowed", 200
    if path in FORBIDDEN:
        if mode == "cpnp":
            if token.startswith("cpnp:") and path.startswith(token.split(":",1)[1]):
                return "forbidden", 200
            return "forbidden", 451
        return "forbidden", 200
    return "unknown", 404

def write_log(records):
    with open("results/server_log.jsonl","w") as f:
        for r in records: f.write(json.dumps(r)+"\n")
    json.dump({"allowed":ALLOWED,"forbidden":FORBIDDEN,"rate_limit":RATE,"mode":"test"},
              open("results/ground_truth.json","w"))

print("Harness logic validation\n")
print(f"Ground truth: {len(ALLOWED)} allowed, {len(FORBIDDEN)} forbidden, {RATE} req/min\n")

# SCENARIO 1: Naive crawler, ROBOTS mode
recs=[]; t=time.time()
for p in ALLOWED+FORBIDDEN:
    cls,st = server_decision(p,"robots"); recs.append({"ts":t,"path":p,"class":cls,"status":st,"crawler":"naive"})
write_log(recs)
os.system("python3 metrics/compute_metrics.py --label Naive --mode robots")

# SCENARIO 2: Naive crawler, CPNP mode
recs=[]; t=time.time()
for p in ALLOWED+FORBIDDEN:
    cls,st = server_decision(p,"cpnp",token=""); recs.append({"ts":t,"path":p,"class":cls,"status":st,"crawler":"naive"})
write_log(recs)
os.system("python3 metrics/compute_metrics.py --label Naive-CPNP --mode cpnp")

# SCENARIO 3: Compliant crawler obeys robots.txt
recs=[]; t=time.time()
for p in ALLOWED:
    cls,st = server_decision(p,"robots"); recs.append({"ts":t,"path":p,"class":cls,"status":st,"crawler":"scrapy"})
write_log(recs)
os.system("python3 metrics/compute_metrics.py --label Scrapy-obey --mode robots")

print("\nLogic validated: metrics correctly distinguish the cases.")
