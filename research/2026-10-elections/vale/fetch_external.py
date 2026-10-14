"""Fetch market data not in the warehouse: Yahoo daily adjusted closes (USD) and FRED monthly commodity prices.
Saves to data/. Run once; vale_study.py reads the CSVs."""
import json, subprocess, pandas as pd
from pathlib import Path
H = Path(__file__).parent / "data"; H.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0"}
def get(url):
    return subprocess.run(["curl", "-s", "--http1.1", "--retry", "3", "-m", "90"] + ([] if "fred" in url else ["-A", UA["User-Agent"]]) + [url], capture_output=True, check=True).stdout
src = {}
for t in ["VALE", "PBR", "BHP", "RIO", "EWZ", "SPY", "XOM"]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1=946684800&period2=1791763200&interval=1d&events=div,split"
    j = json.loads(get(url))["chart"]["result"][0]
    ts = pd.to_datetime(j["timestamp"], unit="s").normalize()
    df = pd.DataFrame({"date": ts, "close": j["indicators"]["quote"][0]["close"],
                       "adjclose": j["indicators"]["adjclose"][0]["adjclose"]}).dropna()
    df.to_csv(H / f"yahoo_{t}.csv", index=False); src[t] = url
    print(t, df.date.min().date(), df.date.max().date(), len(df))
for s in ["PIORECRUSDM", "POILBREUSDM"]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}"
    (H / f"fred_{s}.csv").write_bytes(get(url)); src[s] = url
    print(s, pd.read_csv(H / f"fred_{s}.csv").tail(1).values)
json.dump(src, open(H / "sources.json", "w"), indent=1)
