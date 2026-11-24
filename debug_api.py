from urllib import request as urllib_req, parse as urllib_parse
from http.cookiejar import CookieJar
import json

cj = CookieJar()
opener = urllib_req.build_opener(urllib_req.HTTPCookieProcessor(cj))
base_url = "http://localhost:8000"
try:
    opener.open(f"{base_url}/login", timeout=2)
except Exception:
    base_url = "http://192.168.1.5:8000"

data = urllib_parse.urlencode({"username": "operator", "password": "operator123"}).encode("utf-8")
req = urllib_req.Request(f"{base_url}/login", data=data)
opener.open(req, timeout=5)

resp = opener.open(f"{base_url}/api/operator/payments?period_str=2026-03", timeout=30)
data_json = json.loads(resp.read().decode("utf-8"))

# Show first 5 rows
print("=== Sample rows ===")
for r in data_json.get("rows", [])[:5]:
    sid = r.get("supplier_id")
    net = r.get("net_payable")
    print(f"  ID: {repr(sid)}, net_payable: {net}")

# Find supplier 1/01
print("\n=== Looking for supplier 01 ===")
for r in data_json.get("rows", []):
    sid = str(r.get("supplier_id", "")).strip()
    if sid in ("1", "01", "001"):
        print(f"  Found: ID={repr(sid)}, net_payable={r.get('net_payable')}")
        break

# Show all negative/debt suppliers
print("\n=== All debt suppliers (negative net_payable) ===")
count = 0
for r in data_json.get("rows", []):
    net = r.get("net_payable", 0)
    if net < 0:
        sid = str(r.get("supplier_id", "")).strip()
        print(f"  ID: {repr(sid)}, net_payable: {net}")
        count += 1
print(f"  Total debt suppliers: {count}")
