import json, urllib.request, urllib.parse, sys, time, ssl, certifi
CTX=ssl.create_default_context(cafile=certifi.where())
F = ["document_number","publication_date","signing_date","title","executive_order_number","html_url","citation","type","effective_on","proclamation_number","agencies"]
def fr(name, cond):
    q = [("per_page","100"),("order","oldest")] + [("fields[]",f) for f in F] + cond
    url = "https://www.federalregister.gov/api/v1/documents.json?" + urllib.parse.urlencode(q)
    raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"}), timeout=60, context=CTX).read()
    open(f"{name}.json","wb").write(raw); j = json.loads(raw)
    print("==", name, j.get("count"))
    for r in j.get("results", []):
        print(r["document_number"], r["publication_date"], r.get("signing_date"), r.get("executive_order_number") or r.get("proclamation_number") or "", r.get("citation"), r["type"][:6], r["title"][:120])
    time.sleep(1)
    return j
fr("list_presdocu_brazil", [("conditions[term]","Brazil"),("conditions[type][]","PRESDOCU"),("conditions[publication_date][gte]","2025-04-01")])
fr("list_ustr_brazil301", [("conditions[term]","Brazil Section 301"),("conditions[agencies][]","trade-representative-office-of-united-states"),("conditions[publication_date][gte]","2025-04-01")])
fr("list_232", [("conditions[term]",'"Section 232" imports adjusting'),("conditions[type][]","PRESDOCU"),("conditions[publication_date][gte]","2025-01-15")])
fr("list_ag_reciprocal", [("conditions[term]","agricultural products reciprocal"),("conditions[type][]","PRESDOCU"),("conditions[publication_date][gte]","2025-11-01"),("conditions[publication_date][lte]","2025-12-31")])
fr("list_forced_labor_301", [("conditions[term]","forced labor Section 301"),("conditions[publication_date][gte]","2026-01-01")])
fr("list_section122", [("conditions[term]","Section 122 balance of payments"),("conditions[type][]","PRESDOCU"),("conditions[publication_date][gte]","2026-01-01")])
