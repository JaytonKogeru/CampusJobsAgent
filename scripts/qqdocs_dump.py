# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import re
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/138 Safari/537.36"


def fetch_raw(pad_id: str, sub_id: str, endrow: int) -> str:
    params = {
        "u": "", "noEscape": "1", "enableSmartsheetSplit": "1", "supportOptimizedVer": "4",
        "chunkCellSize": "15000", "normal": "1", "outformat": "1", "wb": "1", "nowb": "0",
        "callback": "x", "xsrf": "", "id": pad_id, "subId": sub_id,
        "startrow": "0", "endrow": str(endrow),
    }
    url = "https://docs.qq.com/dop-api/opendoc?" + urllib.parse.urlencode(params)
    ref = f"https://docs.qq.com/smartsheet/{pad_id}?tab={sub_id}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": ref, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8", "ignore")
    m = re.match(r"^[^(]*\((.*)\)\s*;?\s*$", text, re.S)
    if not m:
        raise RuntimeError("Tencent Docs JSONP parse failed")
    data = json.loads(m.group(1))
    t = (((data.get("clientVars") or {}).get("collab_client_vars") or {}).get("initialAttributedText") or {}).get("text") or []
    if not t or not isinstance(t[0], dict) or not t[0].get("smartsheet"):
        raise RuntimeError("Tencent Docs response has no smartsheet payload")
    b64 = str(t[0]["smartsheet"]).replace("\n", "").replace("\r", "").replace(" ", "")
    raw = base64.b64decode(b64 + "=" * (-len(b64) % 4))
    for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
        try:
            return zlib.decompress(raw, wbits).decode("utf-8", "ignore")
        except zlib.error:
            continue
    raise RuntimeError("Tencent Docs zlib decompression failed")


def field_value(fv, meta):
    if not isinstance(fv, dict):
        return ""
    t = meta.get("type")
    try:
        if t == 1:
            arr = fv.get("k1") or []
            if isinstance(arr, list):
                return "".join((x.get("k2") or x.get("k1") or "") for x in arr if isinstance(x, dict))
            return str(arr)
        if t == 4:
            x = fv.get("k4")
            if x is not None:
                n = int(x)
                d = dt.datetime.fromtimestamp(n / 1000 if n > 10**11 else n)
                return d.strftime("%Y-%m-%d")
        if t == 8:
            arr = fv.get("k8") or fv.get("k1")
            if isinstance(arr, str):
                return arr
            if isinstance(arr, list):
                return " ".join(x.get("k2") for x in arr if isinstance(x, dict) and x.get("k2"))
        if t in (9, 17):
            ids = fv.get("k9") or fv.get("k17") or []
            if isinstance(ids, list):
                return "/".join(meta.get("options", {}).get(i, i) for i in ids)
            return str(ids)
        for v in fv.values():
            if isinstance(v, list) and v:
                vals = []
                for x in v:
                    if isinstance(x, dict):
                        vals.append(str(x.get("k2") or x.get("k1") or ""))
                    elif x is not None:
                        vals.append(str(x))
                vals = [x for x in vals if x]
                if vals:
                    return "/".join(vals)
    except Exception:
        return ""
    return ""


def parse_sheet(text: str):
    rows = json.loads(text)
    if not rows or not isinstance(rows[0], list) or len(rows[0]) < 2:
        return [], {}
    h0, h1 = rows[0][0], rows[0][1]
    defs = (((h0.get("c") or {}).get("k3") or {}).get("k3") or {})
    meta = {}
    for fid, d in defs.items():
        if not isinstance(d, dict):
            continue
        opts = {}
        od = d.get("k17") or d.get("k9") or {}
        oa = od.get("k3") if isinstance(od, dict) else None
        if isinstance(oa, list):
            for o in oa:
                if isinstance(o, dict) and o.get("k1") is not None:
                    opts[o.get("k1")] = str(o.get("k2") or o.get("k1"))
        meta[fid] = {"name": str(d.get("k30") or fid), "type": d.get("k31"), "options": opts}
    records = (((h1.get("c") or {}).get("k2") or {}).get("k1") or {})
    out = []
    for rid, node in records.items():
        fields = node.get("k1") if isinstance(node, dict) else node
        if not isinstance(fields, dict):
            continue
        rec = {"_record_id": rid}
        for fid, fv in fields.items():
            m = meta.get(fid)
            if m:
                rec[m["name"]] = field_value(fv, m)
        if len(rec) > 1:
            out.append(rec)
    return out, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pad-id", required=True)
    ap.add_argument("--sub-id", required=True)
    ap.add_argument("--endrow", type=int, default=3000)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    text = fetch_raw(args.pad_id, args.sub_id, args.endrow)
    records, meta = parse_sheet(text)
    obj = {
        "pad_id": args.pad_id,
        "sub_id": args.sub_id,
        "count": len(records),
        "fields": [m["name"] for m in meta.values()],
        "records": records,
    }
    p = Path(args.output)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"count": len(records), "fields": obj["fields"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
