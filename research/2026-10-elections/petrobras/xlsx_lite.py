"""Minimal stdlib xlsx reader (openpyxl is not installed): returns a sheet as a list of rows."""
import re, zipfile, xml.etree.ElementTree as ET
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def sheet_names(path):
    with zipfile.ZipFile(path) as z:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rmap = {r.get("Id"): r.get("Target") for r in rels}
        return [(s.get("name"), "xl/" + rmap[s.get(RNS)].lstrip("/").replace("xl/", ""))
                for s in wb.find("m:sheets", NS)]


def col_idx(ref):
    c = re.match(r"[A-Z]+", ref).group()
    n = 0
    for ch in c:
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_sheet(path, name):
    with zipfile.ZipFile(path) as z:
        ss = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
                ss.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
        target = dict(sheet_names(path))[name]
        root = ET.fromstring(z.read(target))
        rows = []
        for r in root.iter("{%s}row" % NS["m"]):
            row = {}
            for c in r.findall("m:c", NS):
                v = c.find("m:v", NS)
                t = c.get("t")
                if t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
                elif v is None:
                    continue
                elif t == "s":
                    val = ss[int(v.text)]
                elif t in ("str", "b", "e"):
                    val = v.text
                else:
                    try:
                        val = float(v.text)
                    except ValueError:
                        val = v.text
                row[col_idx(c.get("r"))] = val
            if row:
                rows.append([row.get(i) for i in range(max(row) + 1)])
        return rows
