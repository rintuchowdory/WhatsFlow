from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import datetime, asyncio, json, random, os

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# ── In-memory state ──────────────────────────────────────────────
messages = [
    {"id": 1, "from": "+49 176 1234567", "text": "Hello! Is this working?", "status": "received", "time": "22:28:01"},
    {"id": 2, "from": "Bot", "text": "Hi! WhatsFlow is online 🚀", "status": "sent", "time": "22:28:02"},
    {"id": 3, "from": "+49 152 9876543", "text": "What can you do?", "status": "received", "time": "22:29:10"},
    {"id": 4, "from": "Bot", "text": "I can answer questions 24/7!", "status": "sent", "time": "22:29:11"},
    {"id": 5, "from": "+49 176 1234567", "text": "Amazing! Thanks 🙌", "status": "received", "time": "22:30:45"},
]
stats = {"total": 5, "received": 3, "sent": 2, "failed": 0, "users": 2}
hourly = [2, 5, 3, 8, 12, 7, 4, 9, 15, 11, 6, 3, 8, 14, 10, 7, 5, 9, 13, 8, 11, 6, 4, 5]
connected_clients = []

async def broadcast(data):
    dead = []
    for ws in connected_clients:
        try:
            await ws.send_text(json.dumps(data))
        except:
            dead.append(ws)
    for ws in dead:
        connected_clients.remove(ws)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    await websocket.send_text(json.dumps({"type": "init", "messages": messages, "stats": stats, "hourly": hourly}))
    try:
        while True:
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

@app.post("/simulate")
async def simulate_message():
    names = ["+49 176 5551234", "+49 152 7779988", "+49 160 3334455"]
    texts = ["Hello!", "Any updates?", "Thanks 🙏", "How does this work?", "Great bot! 👍", "Need help please"]
    msg = {
        "id": len(messages) + 1,
        "from": random.choice(names),
        "text": random.choice(texts),
        "status": "received",
        "time": datetime.datetime.now().strftime("%H:%M:%S")
    }
    messages.append(msg)
    stats["total"] += 1
    stats["received"] += 1
    reply = {
        "id": len(messages) + 1,
        "from": "Bot",
        "text": "Thanks for your message! I'll get back to you shortly 🤖",
        "status": "sent",
        "time": datetime.datetime.now().strftime("%H:%M:%S")
    }
    messages.append(reply)
    stats["total"] += 1
    stats["sent"] += 1
    await broadcast({"type": "update", "messages": messages[-6:], "stats": stats})
    return {"ok": True}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(HTML)

HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>WhatsFlow Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Outfit:wght@300;400;600;700;900&display=swap" rel="stylesheet"/>
<style>
:root {
  --bg: #080c14;
  --surface: #0f1623;
  --card: #131d2e;
  --border: rgba(0,255,136,0.12);
  --green: #00ff88;
  --green-dim: #00994d;
  --cyan: #00d4ff;
  --yellow: #ffd600;
  --red: #ff4466;
  --text: #e8f4f0;
  --muted: #4a6670;
  --grid: rgba(0,255,136,0.03);
}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{
  background:var(--bg);
  color:var(--text);
  font-family:'Outfit',sans-serif;
  min-height:100vh;
  overflow-x:hidden;
}
body::before{
  content:'';
  position:fixed;inset:0;
  background-image:
    linear-gradient(var(--grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid) 1px, transparent 1px);
  background-size:40px 40px;
  pointer-events:none;
  z-index:0;
}

/* ── HEADER ── */
header{
  position:sticky;top:0;z-index:100;
  background:rgba(8,12,20,0.9);
  backdrop-filter:blur(20px);
  border-bottom:1px solid var(--border);
  padding:1rem 2rem;
  display:flex;align-items:center;justify-content:space-between;
}
.logo{
  display:flex;align-items:center;gap:0.75rem;
}
.logo-icon{
  width:36px;height:36px;
  background:var(--green);
  border-radius:10px;
  display:flex;align-items:center;justify-content:center;
  font-size:1.2rem;
  animation:pulse 2s ease-in-out infinite;
}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(0,255,136,0.4);}50%{box-shadow:0 0 0 8px rgba(0,255,136,0);}}
.logo-text{
  font-family:'Space Mono',monospace;
  font-size:1.1rem;
  font-weight:700;
  color:var(--green);
  letter-spacing:0.05em;
}
.logo-sub{
  font-size:0.65rem;
  color:var(--muted);
  letter-spacing:0.15em;
  text-transform:uppercase;
}
.header-right{display:flex;align-items:center;gap:1rem;}
.status-pill{
  display:flex;align-items:center;gap:0.5rem;
  background:rgba(0,255,136,0.08);
  border:1px solid var(--border);
  border-radius:20px;
  padding:0.4rem 1rem;
  font-family:'Space Mono',monospace;
  font-size:0.7rem;
  color:var(--green);
}
.status-dot{
  width:8px;height:8px;
  background:var(--green);
  border-radius:50%;
  animation:blink 1.5s ease-in-out infinite;
}
@keyframes blink{0%,100%{opacity:1;}50%{opacity:0.3;}}
.time-display{
  font-family:'Space Mono',monospace;
  font-size:0.75rem;
  color:var(--muted);
}

/* ── MAIN ── */
main{
  position:relative;z-index:1;
  padding:2rem;
  max-width:1400px;
  margin:0 auto;
}

/* ── STATS GRID ── */
.stats-grid{
  display:grid;
  grid-template-columns:repeat(4,1fr);
  gap:1rem;
  margin-bottom:2rem;
}
.stat-card{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:16px;
  padding:1.5rem;
  position:relative;
  overflow:hidden;
  transition:transform 0.3s,border-color 0.3s;
}
.stat-card::before{
  content:'';
  position:absolute;
  top:-50%;right:-50%;
  width:100%;height:100%;
  background:radial-gradient(circle, var(--accent-color,rgba(0,255,136,0.06)) 0%, transparent 70%);
  pointer-events:none;
}
.stat-card:hover{transform:translateY(-3px);border-color:rgba(0,255,136,0.25);}
.stat-label{
  font-size:0.7rem;
  letter-spacing:0.15em;
  text-transform:uppercase;
  color:var(--muted);
  margin-bottom:0.75rem;
  font-family:'Space Mono',monospace;
}
.stat-value{
  font-size:2.5rem;
  font-weight:900;
  line-height:1;
  margin-bottom:0.5rem;
}
.stat-change{
  font-size:0.75rem;
  color:var(--muted);
}
.stat-change span{color:var(--green);}
.stat-card.total .stat-value{color:var(--green);}
.stat-card.received .stat-value{color:var(--cyan);}
.stat-card.sent .stat-value{color:var(--yellow);}
.stat-card.users .stat-value{color:#b088ff;}

/* ── CHART + MESSAGES GRID ── */
.main-grid{
  display:grid;
  grid-template-columns:1fr 1.2fr;
  gap:1.5rem;
  margin-bottom:1.5rem;
}

/* ── PANEL ── */
.panel{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:16px;
  overflow:hidden;
}
.panel-header{
  display:flex;align-items:center;justify-content:space-between;
  padding:1.2rem 1.5rem;
  border-bottom:1px solid var(--border);
}
.panel-title{
  font-family:'Space Mono',monospace;
  font-size:0.8rem;
  letter-spacing:0.1em;
  text-transform:uppercase;
  color:var(--green);
}
.panel-badge{
  font-family:'Space Mono',monospace;
  font-size:0.65rem;
  background:rgba(0,255,136,0.1);
  border:1px solid var(--border);
  color:var(--green);
  padding:0.2rem 0.6rem;
  border-radius:20px;
}

/* ── CHART ── */
.chart-wrap{padding:1.5rem;}
.chart-bars{
  display:flex;
  align-items:flex-end;
  gap:3px;
  height:140px;
  margin-bottom:0.5rem;
}
.bar-col{flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;}
.bar{
  width:100%;
  background:linear-gradient(to top, var(--green-dim), var(--green));
  border-radius:3px 3px 0 0;
  transition:height 0.5s ease;
  min-height:4px;
  position:relative;
  cursor:pointer;
}
.bar:hover{background:linear-gradient(to top,var(--cyan),#88ffee);}
.bar-label{
  font-family:'Space Mono',monospace;
  font-size:0.5rem;
  color:var(--muted);
}
.chart-legend{
  display:flex;gap:1.5rem;
  margin-top:1rem;
  padding-top:1rem;
  border-top:1px solid var(--border);
}
.legend-item{
  display:flex;align-items:center;gap:0.4rem;
  font-size:0.7rem;
  color:var(--muted);
}
.legend-dot{width:8px;height:8px;border-radius:50%;}

/* ── MESSAGES ── */
.messages-list{
  padding:1rem;
  display:flex;
  flex-direction:column;
  gap:0.6rem;
  max-height:340px;
  overflow-y:auto;
}
.messages-list::-webkit-scrollbar{width:4px;}
.messages-list::-webkit-scrollbar-track{background:transparent;}
.messages-list::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px;}
.msg-item{
  display:flex;
  gap:0.75rem;
  padding:0.75rem;
  border-radius:10px;
  background:rgba(255,255,255,0.02);
  border:1px solid transparent;
  transition:all 0.3s;
  animation:slideIn 0.4s ease;
}
@keyframes slideIn{from{opacity:0;transform:translateX(-10px);}to{opacity:1;transform:translateX(0);}}
.msg-item:hover{background:rgba(0,255,136,0.04);border-color:var(--border);}
.msg-avatar{
  width:32px;height:32px;min-width:32px;
  border-radius:8px;
  display:flex;align-items:center;justify-content:center;
  font-size:0.8rem;
  font-weight:700;
}
.msg-avatar.received{background:rgba(0,212,255,0.15);color:var(--cyan);}
.msg-avatar.sent{background:rgba(0,255,136,0.15);color:var(--green);}
.msg-body{flex:1;min-width:0;}
.msg-from{
  font-family:'Space Mono',monospace;
  font-size:0.65rem;
  color:var(--muted);
  margin-bottom:0.2rem;
}
.msg-text{
  font-size:0.85rem;
  color:var(--text);
  line-height:1.4;
  word-break:break-word;
}
.msg-time{
  font-family:'Space Mono',monospace;
  font-size:0.6rem;
  color:var(--muted);
  white-space:nowrap;
  align-self:flex-end;
}
.msg-status{
  display:inline-block;
  font-size:0.6rem;
  padding:0.15rem 0.4rem;
  border-radius:4px;
  font-family:'Space Mono',monospace;
  margin-top:0.2rem;
}
.msg-status.received{background:rgba(0,212,255,0.1);color:var(--cyan);}
.msg-status.sent{background:rgba(0,255,136,0.1);color:var(--green);}

/* ── BOTTOM GRID ── */
.bottom-grid{
  display:grid;
  grid-template-columns:1fr 1fr 1fr;
  gap:1.5rem;
}

/* ── WORKFLOW ── */
.workflow-list{padding:1rem;}
.workflow-item{
  display:flex;align-items:center;gap:1rem;
  padding:0.85rem;
  border-radius:10px;
  border:1px solid transparent;
  margin-bottom:0.5rem;
  transition:all 0.3s;
}
.workflow-item:hover{background:rgba(0,255,136,0.03);border-color:var(--border);}
.wf-icon{
  width:36px;height:36px;min-width:36px;
  border-radius:8px;
  display:flex;align-items:center;justify-content:center;
  font-size:1rem;
}
.wf-info{flex:1;}
.wf-name{font-size:0.85rem;font-weight:600;margin-bottom:0.2rem;}
.wf-time{font-family:'Space Mono',monospace;font-size:0.6rem;color:var(--muted);}
.wf-badge{
  font-family:'Space Mono',monospace;
  font-size:0.6rem;
  padding:0.2rem 0.6rem;
  border-radius:20px;
  font-weight:700;
}
.wf-badge.completed{background:rgba(0,255,136,0.1);color:var(--green);border:1px solid rgba(0,255,136,0.2);}
.wf-badge.running{background:rgba(255,214,0,0.1);color:var(--yellow);border:1px solid rgba(255,214,0,0.2);}
.wf-badge.failed{background:rgba(255,68,102,0.1);color:var(--red);border:1px solid rgba(255,68,102,0.2);}

/* ── MINI STATS ── */
.mini-stat{
  display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  padding:2rem 1rem;
  text-align:center;
}
.mini-ring{
  width:100px;height:100px;
  position:relative;
  margin-bottom:1rem;
}
.mini-ring svg{transform:rotate(-90deg);}
.ring-bg{fill:none;stroke:rgba(0,255,136,0.1);stroke-width:8;}
.ring-fill{
  fill:none;
  stroke:var(--green);
  stroke-width:8;
  stroke-linecap:round;
  stroke-dasharray:251;
  stroke-dashoffset:25;
  transition:stroke-dashoffset 1s ease;
  filter:drop-shadow(0 0 4px var(--green));
}
.ring-text{
  position:absolute;inset:0;
  display:flex;flex-direction:column;
  align-items:center;justify-content:center;
}
.ring-val{font-size:1.4rem;font-weight:900;color:var(--green);}
.ring-lbl{font-size:0.55rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.1em;}
.mini-desc{font-size:0.75rem;color:var(--muted);}

/* ── SIM BUTTON ── */
.sim-panel{padding:1.5rem;display:flex;flex-direction:column;gap:1rem;}
.sim-btn{
  width:100%;
  padding:1rem;
  background:linear-gradient(135deg,var(--green-dim),var(--green));
  border:none;
  border-radius:10px;
  color:#080c14;
  font-family:'Space Mono',monospace;
  font-size:0.8rem;
  font-weight:700;
  letter-spacing:0.1em;
  cursor:pointer;
  transition:all 0.3s;
  text-transform:uppercase;
}
.sim-btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,255,136,0.3);}
.sim-btn:active{transform:translateY(0);}
.ws-indicator{
  display:flex;align-items:center;gap:0.5rem;
  font-family:'Space Mono',monospace;
  font-size:0.65rem;
  color:var(--muted);
  padding:0.75rem;
  background:rgba(0,255,136,0.04);
  border:1px solid var(--border);
  border-radius:8px;
}
.ws-dot{width:6px;height:6px;border-radius:50%;background:var(--red);}
.ws-dot.connected{background:var(--green);animation:blink 1.5s infinite;}
.info-box{
  padding:0.75rem;
  background:rgba(0,212,255,0.04);
  border:1px solid rgba(0,212,255,0.15);
  border-radius:8px;
  font-size:0.75rem;
  color:var(--muted);
  line-height:1.6;
}
.info-box strong{color:var(--cyan);}

@media(max-width:1024px){
  .stats-grid{grid-template-columns:repeat(2,1fr);}
  .main-grid{grid-template-columns:1fr;}
  .bottom-grid{grid-template-columns:1fr;}
}
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-icon">💬</div>
    <div>
      <div class="logo-text">WhatsFlow</div>
      <div class="logo-sub">Dashboard v2.0</div>
    </div>
  </div>
  <div class="header-right">
    <div class="status-pill"><div class="status-dot"></div>Bot Online</div>
    <div class="time-display" id="clock">--:--:--</div>
  </div>
</header>

<main>

  <!-- STATS -->
  <div class="stats-grid">
    <div class="stat-card total">
      <div class="stat-label">Total Messages</div>
      <div class="stat-value" id="s-total">0</div>
      <div class="stat-change">Today <span>+12%</span></div>
    </div>
    <div class="stat-card received">
      <div class="stat-label">Received</div>
      <div class="stat-value" id="s-received">0</div>
      <div class="stat-change">Inbound <span>active</span></div>
    </div>
    <div class="stat-card sent">
      <div class="stat-label">Sent</div>
      <div class="stat-value" id="s-sent">0</div>
      <div class="stat-change">Outbound <span>ok</span></div>
    </div>
    <div class="stat-card users">
      <div class="stat-label">Active Users</div>
      <div class="stat-value" id="s-users">0</div>
      <div class="stat-change">Unique <span>today</span></div>
    </div>
  </div>

  <!-- CHART + MESSAGES -->
  <div class="main-grid">

    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">📊 Hourly Activity</div>
        <div class="panel-badge">24h</div>
      </div>
      <div class="chart-wrap">
        <div class="chart-bars" id="chart-bars"></div>
        <div class="chart-legend">
          <div class="legend-item"><div class="legend-dot" style="background:var(--green)"></div>Messages</div>
          <div class="legend-item"><div class="legend-dot" style="background:var(--cyan)"></div>Peak Hour</div>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">💬 Live Messages</div>
        <div class="panel-badge" id="msg-count">0 total</div>
      </div>
      <div class="messages-list" id="messages-list"></div>
    </div>

  </div>

  <!-- BOTTOM ROW -->
  <div class="bottom-grid">

    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">⚡ Workflow Status</div>
      </div>
      <div class="workflow-list">
        <div class="workflow-item">
          <div class="wf-icon" style="background:rgba(0,255,136,0.1)">🚀</div>
          <div class="wf-info">
            <div class="wf-name">Bot Engine</div>
            <div class="wf-time">Started 22:31:00</div>
          </div>
          <div class="wf-badge completed">Completed</div>
        </div>
        <div class="workflow-item">
          <div class="wf-icon" style="background:rgba(255,214,0,0.1)">👂</div>
          <div class="wf-info">
            <div class="wf-name">Message Listener</div>
            <div class="wf-time">Running since boot</div>
          </div>
          <div class="wf-badge running">Running</div>
        </div>
        <div class="workflow-item">
          <div class="wf-icon" style="background:rgba(0,212,255,0.1)">🔗</div>
          <div class="wf-info">
            <div class="wf-name">Webhook Handler</div>
            <div class="wf-time">Awaiting config</div>
          </div>
          <div class="wf-badge running">Pending</div>
        </div>
        <div class="workflow-item">
          <div class="wf-icon" style="background:rgba(176,136,255,0.1)">🗄️</div>
          <div class="wf-info">
            <div class="wf-name">CI/CD Pipeline</div>
            <div class="wf-time">GitHub Actions</div>
          </div>
          <div class="wf-badge completed">Active</div>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">📈 Response Rate</div>
      </div>
      <div class="mini-stat">
        <div class="mini-ring">
          <svg width="100" height="100" viewBox="0 0 100 100">
            <circle class="ring-bg" cx="50" cy="50" r="40"/>
            <circle class="ring-fill" id="ring-fill" cx="50" cy="50" r="40"/>
          </svg>
          <div class="ring-text">
            <div class="ring-val">90%</div>
            <div class="ring-lbl">Rate</div>
          </div>
        </div>
        <div class="mini-desc">Bot responds to 90% of messages within 1 second</div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">🎮 Controls</div>
      </div>
      <div class="sim-panel">
        <div class="ws-indicator">
          <div class="ws-dot" id="ws-dot"></div>
          <span id="ws-status">WebSocket: Connecting...</span>
        </div>
        <button class="sim-btn" onclick="simulate()">⚡ Simulate Message</button>
        <div class="info-box">
          <strong>WhatsApp Cloud API</strong><br/>
          Connect via Meta Developer Portal to receive real messages. Webhook URL:<br/>
          <code style="color:var(--green);font-size:0.7rem">http://your-server:8000/webhook</code>
        </div>
      </div>
    </div>

  </div>
</main>

<script>
// ── Clock ──────────────────────────────────────────────────────
function tick(){
  document.getElementById('clock').textContent =
    new Date().toLocaleTimeString('de-DE');
}
tick(); setInterval(tick,1000);

// ── WebSocket ─────────────────────────────────────────────────
let ws;
function connect(){
  ws = new WebSocket('ws://' + location.host + '/ws');
  ws.onopen = () => {
    document.getElementById('ws-dot').classList.add('connected');
    document.getElementById('ws-status').textContent = 'WebSocket: Connected ✓';
  };
  ws.onclose = () => {
    document.getElementById('ws-dot').classList.remove('connected');
    document.getElementById('ws-status').textContent = 'WebSocket: Reconnecting...';
    setTimeout(connect, 3000);
  };
  ws.onmessage = e => {
    const d = JSON.parse(e.data);
    if(d.type === 'init'){
      updateStats(d.stats);
      renderMessages(d.messages);
      renderChart(d.hourly);
    } else if(d.type === 'update'){
      updateStats(d.stats);
      renderMessages(d.messages, true);
    }
  };
}
connect();

// ── Stats ─────────────────────────────────────────────────────
function animCount(el, target){
  let v = parseInt(el.textContent)||0, step = Math.max(1, Math.ceil((target-v)/20));
  const t = setInterval(()=>{
    v = Math.min(v+step, target);
    el.textContent = v;
    if(v >= target) clearInterval(t);
  }, 50);
}
function updateStats(s){
  animCount(document.getElementById('s-total'), s.total);
  animCount(document.getElementById('s-received'), s.received);
  animCount(document.getElementById('s-sent'), s.sent);
  animCount(document.getElementById('s-users'), s.users);
  document.getElementById('msg-count').textContent = s.total + ' total';
}

// ── Messages ──────────────────────────────────────────────────
function renderMessages(msgs, append=false){
  const list = document.getElementById('messages-list');
  if(!append) list.innerHTML = '';
  const show = append ? msgs : msgs.slice(-10);
  show.forEach(m => {
    const isBot = m.from === 'Bot';
    const div = document.createElement('div');
    div.className = 'msg-item';
    div.innerHTML = `
      <div class="msg-avatar ${m.status}">${isBot ? '🤖' : '👤'}</div>
      <div class="msg-body">
        <div class="msg-from">${m.from}</div>
        <div class="msg-text">${m.text}</div>
        <span class="msg-status ${m.status}">${m.status}</span>
      </div>
      <div class="msg-time">${m.time}</div>
    `;
    list.appendChild(div);
  });
  list.scrollTop = list.scrollHeight;
}

// ── Chart ─────────────────────────────────────────────────────
function renderChart(hourly){
  const max = Math.max(...hourly);
  const container = document.getElementById('chart-bars');
  container.innerHTML = '';
  const hours = ['0','1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18','19','20','21','22','23'];
  hourly.forEach((val,i) => {
    const pct = max > 0 ? (val/max)*100 : 0;
    const isMax = val === max;
    const col = document.createElement('div');
    col.className = 'bar-col';
    col.innerHTML = `
      <div class="bar" style="height:${pct}%;${isMax?'background:linear-gradient(to top,var(--cyan),#88ffee);':''}" title="${val} messages at ${hours[i]}:00"></div>
      <div class="bar-label">${i%4===0?hours[i]:''}</div>
    `;
    container.appendChild(col);
  });
}

// ── Simulate ──────────────────────────────────────────────────
async function simulate(){
  const btn = document.querySelector('.sim-btn');
  btn.textContent = '⏳ Sending...';
  btn.disabled = true;
  await fetch('/simulate', {method:'POST'});
  setTimeout(()=>{btn.textContent='⚡ Simulate Message';btn.disabled=false;}, 1000);
}
</script>
</body>
</html>
'''
