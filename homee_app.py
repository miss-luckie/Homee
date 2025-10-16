#!/usr/bin/env python3
# HOMEe Web App (display-only; local time, blinking boxes, banner, trends)
 
from flask import Flask, jsonify, render_template_string, request
import csv, os
from typing import List, Dict, Any
 
app = Flask(__name__)
 
LOG_FILE = "/home/raspberry01/homee/homee_readings.csv"
MAX_HISTORY = 500  # server-side cap for safety
 
def _read_tail(limit:int)->List[Dict[str,Any]]:
    if not os.path.exists(LOG_FILE):
        return []
    rows=[]
    with open(LOG_FILE,"r",newline="") as f:
        r=csv.DictReader(f)
        for row in r:
            rows.append(row)
    rows=rows[-min(limit,MAX_HISTORY):]
    out=[]
    for row in rows:
        try:
            out.append({
                "timestamp": int(row.get("timestamp", 0) or 0),
                "datetime_utc": row.get("datetime_utc",""),
                "temp_c": float(row.get("temperature_C","") or "nan"),
                "humidity": float(row.get("humidity_pct","") or "nan"),
                "temp_band": {
                    "color": row.get("temp_color",""),
                    "mode":  row.get("temp_mode",""),
                    "message": row.get("temp_message",""),
                },
                "hum_band": {
                    "color": row.get("hum_color",""),
                    "mode":  row.get("hum_mode",""),
                    "message": row.get("hum_message",""),
                },
            })
        except Exception:
            continue
    return out
 
@app.route("/")
def index():
    return render_template_string("""
<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HOMEe Dashboard</title>
<style>
  :root{
    --bg:#0f172a; --card:#0b1022; --text:#e5e7eb; --muted:#94a3b8;
    --radius:14px; font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
  }
  body{background:linear-gradient(180deg,#0b1022,#0f172a 60%);color:var(--text);margin:0}
  .hero{
    background: radial-gradient(1200px 400px at 20% -20%, rgba(96,165,250,.25), transparent),
                radial-gradient(1200px 400px at 80% -10%, rgba(168,85,247,.20), transparent),
                #0b1022;
    padding:28px 20px 18px 20px; color:#fff; position:sticky; top:0; z-index:2;
    border-bottom:1px solid rgba(255,255,255,0.06);
  }
  .hero h1{margin:0; font-size:28px; letter-spacing:.3px}
  .hero .sub{margin-top:8px; color:var(--muted)}
  .wrap{padding:20px}
  .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;}
  .card{
    background:var(--card); border-radius:var(--radius); padding:18px;
    box-shadow:0 6px 20px rgba(0,0,0,.35); border:1px solid rgba(255,255,255,.06);
    transition:transform .2s, box-shadow .2s;
  }
  .card:hover{transform:translateY(-3px); box-shadow:0 10px 28px rgba(0,0,0,.45);}
  .k{color:var(--muted); font-size:14px}
  .value{font-size:38px; font-weight:800; letter-spacing:.3px; display:flex; align-items:baseline; gap:10px}
  .arrow{font-size:20px; opacity:.8}
  #tempBox,#humBox{
    border-radius:var(--radius); color:#fff; text-shadow:0 1px 2px rgba(0,0,0,.5);
    border:1px solid rgba(255,255,255,.08);
  }
  @keyframes pulse { 0%{opacity:1} 50%{opacity:.55} 100%{opacity:1} }
  .blink1{ animation:pulse 1s ease-in-out infinite; }
  .blink5{ animation:pulse 5s ease-in-out infinite; }
 
  table{width:100%; border-collapse:collapse; margin-top:18px;}
  th,td{border-bottom:1px solid rgba(255,255,255,.08); padding:10px; font-size:14px}
  th{color:#cbd5e1; text-align:left; background:rgba(255,255,255,.03)}
  select{
    padding:6px 10px; border-radius:8px; border:1px solid rgba(255,255,255,.18);
    background:#0f172a; color:var(--text)
  }
</style>
</head>
<body>
  <div class="hero">
    <h1>HOMEe Dashboard</h1>
    <div class="sub">Last update: <span id="lastLocal">—</span></div>
  </div>
 
  <div class="wrap">
    <div class="cards">
      <div class="card" id="tempBox">
        <div class="k">Temperature</div>
        <div class="value">
          <span id="t">—</span> °C
          <span id="tArrow" class="arrow">–</span>
        </div>
        <div id="tmsg" class="k" style="margin-top:6px;">—</div>
      </div>
      <div class="card" id="humBox">
        <div class="k">Humidity</div>
        <div class="value">
          <span id="h">—</span> %
          <span id="hArrow" class="arrow">–</span>
        </div>
        <div id="hmsg" class="k" style="margin-top:6px;">—</div>
      </div>
    </div>
 
    <h3 style="margin:22px 0 8px 0;">Recent readings</h3>
    <label class="k">Show last
      <select id="limitSel">
        <option selected>50</option><option>100</option><option>200</option><option>500</option>
      </select> entries
    </label>
 
    <table>
      <thead><tr><th>Local time</th><th>°C</th><th>%</th><th>Temp status</th><th>Hum status</th></tr></thead>
      <tbody id="recent"></tbody>
    </table>
  </div>
 
<script>
function ledColor(c){
  switch(c){
    case "RED":return "#ef4444";
    case "ORANGE":return "#f59e0b";
    case "YELLOW":return "#facc15";
    case "GREEN":return "#22c55e";
    case "BLUE":return "#3b82f6";
    case "PURPLE":return "#a855f7";
    default:return "#64748b";
  }
}
function localStrFromTS(ts){
  if(!ts) return '';
  return new Date(ts*1000).toLocaleString();
}
function trendArrow(curr, prev, eps){
  if(prev == null || isNaN(prev)) return "–";
  const d = curr - prev;
  if (d > eps)  return "▲";
  if (d < -eps) return "▼";
  return "→";
}
function applyBlink(el, mode){
  el.classList.remove('blink1','blink5');
  if(mode === 'flash1') el.classList.add('blink1');
  else if(mode === 'flash5') el.classList.add('blink5');
}
 
async function load(limit){
  try{
    const res = await fetch('/data?limit='+limit);
    const obj = await res.json();
    const hist = obj.history || [];
    const cur  = obj.current || {};
    const prev = hist.length > 1 ? hist[1] : null; // newest first
 
    document.getElementById('lastLocal').textContent = localStrFromTS(cur.timestamp);
    document.getElementById('t').textContent = (cur.temp_c ?? '—');
    document.getElementById('h').textContent = (cur.humidity ?? '—');
 
    const tPrev = prev ? prev.temp_c : null;
    const hPrev = prev ? prev.humidity : null;
    document.getElementById('tArrow').textContent = trendArrow(cur.temp_c, tPrev, 0.1);
    document.getElementById('hArrow').textContent = trendArrow(cur.humidity, hPrev, 0.5);
 
    const tb = cur.temp_band || {}, hb = cur.hum_band || {};
    document.getElementById('tmsg').textContent = tb.message || '';
    document.getElementById('hmsg').textContent = hb.message || '';
 
    const tBox = document.getElementById('tempBox');
    const hBox = document.getElementById('humBox');
    tBox.style.background = ledColor(tb.color);
    hBox.style.background = ledColor(hb.color);
    applyBlink(tBox, tb.mode);
    applyBlink(hBox, hb.mode);
 
    const body = document.getElementById('recent');
    body.innerHTML = '';
    hist.forEach((r)=>{
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${localStrFromTS(r.timestamp)}</td>
        <td>${r.temp_c ?? ''}</td>
        <td>${r.humidity ?? ''}</td>
        <td>${(r.temp_band?.message || '')}</td>
        <td>${(r.hum_band?.message || '')}</td>`;
      body.appendChild(tr);
    });
 
  }catch(e){ console.error(e); }
}
 
const sel = document.getElementById('limitSel');
sel.addEventListener('change', ()=>load(parseInt(sel.value,10)));
load(parseInt(sel.value,10));                  // default 50
setInterval(()=>load(parseInt(sel.value,10)), 5000);
</script>
</body></html>
""")
 
@app.route("/data")
def data():
    try:
        limit = int(request.args.get("limit","50"))  # default 50
    except:
        limit = 50
    hist = _read_tail(limit)
    return jsonify({
        "current": (hist[-1] if hist else {}),
        "history": hist[::-1]  # newest first
    })
 
@app.route("/submit", methods=["POST"])
def submit():
    # No-op; device already logs to CSV
    _ = request.get_json(silent=True)
    return jsonify({"ok": True})
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
