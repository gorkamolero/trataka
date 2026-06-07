#!/usr/bin/env python3
"""Build a single self-contained HTML findings report from the DuckDB store.

Everything (data + styles + script) is inlined, so the file opens by
double-clicking — no web server, no GitHub, no CDN. Includes a search box,
LLC / small-band / staffing filters, sortable columns, and a Google Maps link
per company.

Usage: python scripts/build_report_html.py [--db visa_finder.duckdb] [--out findings.html]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from visa_finder.store import Store

COLS = [
    "name", "entity_type", "is_staffing", "city", "state", "zip", "naics_code",
    "lca_filing_count", "in_target_band", "size_confidence", "review_status",
    "address", "latitude", "longitude",
]


def build(db: str, out: str) -> int:
    s = Store(db)
    rows = s.con.execute(
        f"SELECT {','.join(COLS)} FROM companies "
        "ORDER BY (entity_type='LLC') DESC, COALESCE(in_target_band,FALSE) DESC, "
        "lca_filing_count ASC, name"
    ).fetchall()
    data = [dict(zip(COLS, r, strict=False)) for r in rows]
    payload = json.dumps(data).replace("</", "<\\/")

    html = _TEMPLATE.replace("__DATA__", payload).replace("__COUNT__", str(len(data)))
    Path(out).write_text(html)
    return len(data)


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>H1B Small-Software-Sponsor Finder — Findings</title>
<style>
  :root{--bg:#0f1419;--panel:#171c24;--line:#2a313c;--text:#e6e9ef;--muted:#9aa4b2;--accent:#4f9cff;--llc:#36c98d;}
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--text)}
  header{padding:16px 20px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:5}
  h1{font-size:18px;margin:0 0 4px}
  .sub{color:var(--muted);font-size:13px;margin:0 0 10px}
  .controls{display:flex;gap:14px;flex-wrap:wrap;align-items:center}
  input[type=search]{background:var(--panel);border:1px solid var(--line);color:var(--text);padding:8px 10px;border-radius:8px;min-width:260px;font-size:14px}
  label{font-size:13px;color:var(--text);display:flex;align-items:center;gap:6px;cursor:pointer}
  .count{color:var(--muted);font-size:13px;margin-left:auto}
  .wrap{padding:0 20px 40px}
  table{border-collapse:collapse;width:100%;font-size:13px}
  th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
  th{position:sticky;top:96px;background:var(--panel);cursor:pointer;user-select:none}
  th:hover{color:var(--accent)}
  tbody tr:hover{background:#1e2530}
  .llc{color:var(--llc);font-weight:600}
  .tag{font-size:11px;color:var(--muted)}
  a{color:var(--accent);text-decoration:none}
  td.num{text-align:right}
  .yes{color:var(--llc)} .no{color:var(--muted)}
</style>
</head>
<body>
<header>
  <h1>H1B Small-Software-Sponsor Finder — MO &amp; TX</h1>
  <p class="sub">U.S. DOL OFLC LCA disclosure data, FY2022–FY2026 (all 17 quarters, case-deduped). Leads to verify, not ground truth. Headcount is always <em>unknown</em>; "In band" is a filing-volume proxy. Entity type inferred from name.</p>
  <div class="controls">
    <input id="q" type="search" placeholder="Search name / city / NAICS…"/>
    <label><input type="checkbox" id="llc"/> LLC only</label>
    <label><input type="checkbox" id="band"/> Small band (2–10)</label>
    <label><input type="checkbox" id="nostaff" checked/> Hide staffing/consulting</label>
    <span class="count" id="count"></span>
  </div>
</header>
<div class="wrap">
  <table>
    <thead><tr id="head"></tr></thead>
    <tbody id="body"></tbody>
  </table>
</div>
<script>
const DATA = __DATA__;
const COLS = [
  ["name","Company"],["entity_type","Type"],["city","City"],["state","ST"],
  ["naics_code","NAICS"],["lca_filing_count","Filings"],["in_target_band","In band"],
  ["size_confidence","Confidence"],["review_status","Review"],["map","Map"]
];
let sortKey="lca_filing_count", sortAsc=true;

function mapsLink(r){
  const parts=[r.name, r.address, r.city, r.state].filter(Boolean).join(", ");
  return "https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(parts);
}
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}

function head(){
  document.getElementById("head").innerHTML = COLS.map(([k,l])=>`<th data-k="${k}">${l}</th>`).join("");
  document.querySelectorAll("th").forEach(th=>th.onclick=()=>{
    const k=th.dataset.k; if(k==="map")return;
    if(sortKey===k)sortAsc=!sortAsc; else{sortKey=k;sortAsc=true;}
    render();
  });
}
function filtered(){
  const q=document.getElementById("q").value.toLowerCase();
  const llc=document.getElementById("llc").checked;
  const band=document.getElementById("band").checked;
  const nostaff=document.getElementById("nostaff").checked;
  return DATA.filter(r=>{
    if(llc && r.entity_type!=="LLC")return false;
    if(band && r.in_target_band!==true)return false;
    if(nostaff && r.is_staffing===true)return false;
    if(q){
      const hay=(r.name+" "+(r.city||"")+" "+(r.naics_code||"")+" "+(r.state||"")).toLowerCase();
      if(!hay.includes(q))return false;
    }
    return true;
  });
}
function render(){
  const rows=filtered();
  rows.sort((a,b)=>{
    let x=a[sortKey], y=b[sortKey];
    if(x==null)x=""; if(y==null)y="";
    if(typeof x==="number"&&typeof y==="number")return sortAsc?x-y:y-x;
    return sortAsc?String(x).localeCompare(String(y)):String(y).localeCompare(String(x));
  });
  document.getElementById("count").textContent=rows.length+" companies";
  const body=rows.map(r=>{
    const band=r.in_target_band===true?'<span class="yes">yes</span>':(r.in_target_band===false?'<span class="no">no</span>':'<span class="no">—</span>');
    const type=r.entity_type==="LLC"?'<span class="llc">LLC</span>':esc(r.entity_type)+(r.is_staffing?' <span class="tag">(staffing)</span>':'');
    return `<tr>
      <td>${esc(r.name)}</td><td>${type}</td><td>${esc(r.city)}</td><td>${esc(r.state)}</td>
      <td>${esc(r.naics_code)}</td><td class="num">${r.lca_filing_count}</td><td>${band}</td>
      <td>${esc(r.size_confidence)}</td><td>${r.review_status==="needs_review"?"🔎":""}</td>
      <td><a href="${mapsLink(r)}" target="_blank" rel="noopener">📍 Maps</a></td>
    </tr>`;
  }).join("");
  document.getElementById("body").innerHTML=body;
}
head();
["q","llc","band","nostaff"].forEach(id=>document.getElementById(id).addEventListener("input",render));
render();
</script>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="visa_finder.duckdb")
    ap.add_argument("--out", default="findings.html")
    args = ap.parse_args()
    n = build(args.db, args.out)
    print(f"Wrote {n} companies -> {args.out}")


if __name__ == "__main__":
    main()
