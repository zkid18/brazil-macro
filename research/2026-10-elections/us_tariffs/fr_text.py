import json, urllib.request, urllib.parse, sys, time, ssl, certifi, os
CTX=ssl.create_default_context(cafile=certifi.where())
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"}), timeout=120, context=CTX).read()
docs = sys.argv[1:]
for d in docs:
    if os.path.exists(f"{d}.txt") and os.path.getsize(f"{d}.txt")>1000: continue
    m = json.loads(get(f"https://www.federalregister.gov/api/v1/documents/{d}.json?fields[]=raw_text_url&fields[]=pdf_url&fields[]=title&fields[]=publication_date&fields[]=signing_date&fields[]=citation&fields[]=effective_on&fields[]=html_url"))
    open(f"{d}.meta.json","w").write(json.dumps(m))
    t = get(m["raw_text_url"]); open(f"{d}.txt","wb").write(t)
    print(d, m["publication_date"], m.get("citation"), len(t), m["title"][:90]); time.sleep(1)
