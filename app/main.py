from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime, asyncio, json, random, os

# ── Database Setup ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "whatsflow.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Message(Base):
    __tablename__ = "messages"
    id        = Column(Integer, primary_key=True, index=True)
    sender    = Column(String(100), nullable=False)
    text      = Column(Text, nullable=False)
    status    = Column(String(20), default="received")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True)
    phone         = Column(String(50), unique=True, nullable=False)
    first_seen    = Column(DateTime, default=datetime.datetime.utcnow)
    last_seen     = Column(DateTime, default=datetime.datetime.utcnow)
    message_count = Column(Integer, default=0)

Base.metadata.create_all(bind=engine)

def seed_data():
    db = SessionLocal()
    if db.query(Message).count() == 0:
        seeds = [
            Message(sender="+49 176 1234567", text="Hello! Is this working?",    status="received", timestamp=datetime.datetime.now()-datetime.timedelta(minutes=15)),
            Message(sender="Bot",             text="Hi! WhatsFlow is online 🚀", status="sent",     timestamp=datetime.datetime.now()-datetime.timedelta(minutes=14)),
            Message(sender="+49 152 9876543", text="What can you do?",           status="received", timestamp=datetime.datetime.now()-datetime.timedelta(minutes=10)),
            Message(sender="Bot",             text="I can answer questions 24/7!",status="sent",    timestamp=datetime.datetime.now()-datetime.timedelta(minutes=9)),
            Message(sender="+49 176 1234567", text="Amazing! Thanks 🙌",         status="received", timestamp=datetime.datetime.now()-datetime.timedelta(minutes=5)),
            Message(sender="Bot",             text="You're welcome! Type anything to chat.", status="sent", timestamp=datetime.datetime.now()-datetime.timedelta(minutes=4)),
        ]
        db.add_all(seeds)
        db.add_all([User(phone="+49 176 1234567", message_count=2), User(phone="+49 152 9876543", message_count=1)])
        db.commit()
    db.close()

seed_data()

# ── App ───────────────────────────────────────────────────────────
app = FastAPI(title="WhatsFlow API")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

connected_clients = []

async def broadcast(data):
    dead = []
    for ws in connected_clients:
        try: await ws.send_text(json.dumps(data))
        except: dead.append(ws)
    for ws in dead: connected_clients.remove(ws)

def get_stats():
    db = SessionLocal()
    s = {"total": db.query(Message).count(),
         "received": db.query(Message).filter(Message.status=="received").count(),
         "sent": db.query(Message).filter(Message.status=="sent").count(),
         "failed": db.query(Message).filter(Message.status=="failed").count(),
         "users": db.query(User).count()}
    db.close()
    return s

def get_hourly():
    db = SessionLocal()
    now = datetime.datetime.now()
    result = []
    for h in range(24):
        start = now.replace(hour=h, minute=0, second=0, microsecond=0)
        end = start + datetime.timedelta(hours=1)
        result.append(db.query(Message).filter(Message.timestamp >= start, Message.timestamp < end).count())
    db.close()
    return result

def msgs_to_list(msgs):
    return [{"id": m.id, "from": m.sender, "text": m.text, "status": m.status, "time": m.timestamp.strftime("%H:%M:%S")} for m in msgs]

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    db = SessionLocal()
    msgs = db.query(Message).order_by(Message.timestamp.desc()).limit(20).all()
    db.close()
    await websocket.send_text(json.dumps({"type":"init","messages":msgs_to_list(reversed(msgs)),"stats":get_stats(),"hourly":get_hourly()}))
    try:
        while True: await asyncio.sleep(30)
    except WebSocketDisconnect:
        if websocket in connected_clients: connected_clients.remove(websocket)

@app.get("/api/messages")
def api_messages(limit: int = Query(50), search: str = Query("")):
    db = SessionLocal()
    q = db.query(Message).order_by(Message.timestamp.desc())
    if search: q = q.filter(Message.text.contains(search) | Message.sender.contains(search))
    msgs = q.limit(limit).all()
    db.close()
    return msgs_to_list(reversed(msgs))

@app.get("/api/stats")
def api_stats(): return get_stats()

@app.get("/api/users")
def api_users():
    db = SessionLocal()
    users = db.query(User).order_by(User.last_seen.desc()).all()
    db.close()
    return [{"phone": u.phone, "first_seen": str(u.first_seen)[:16], "last_seen": str(u.last_seen)[:16], "messages": u.message_count} for u in users]

@app.post("/simulate")
async def simulate():
    phones = ["+49 176 5551234", "+49 152 7779988", "+49 160 3334455", "+49 176 1234567"]
    texts  = ["Hello!", "Any updates?", "Thanks 🙏", "How does this work?", "Great bot! 👍", "Need help please"]
    phone  = random.choice(phones)
    db     = SessionLocal()
    incoming = Message(sender=phone, text=random.choice(texts), status="received")
    db.add(incoming)
    user = db.query(User).filter(User.phone==phone).first()
    if user: user.last_seen=datetime.datetime.now(); user.message_count+=1
    else: db.add(User(phone=phone, message_count=1))
    reply = Message(sender="Bot", text=random.choice(["Got it! 🤖","Thanks for reaching out!","How can I help? 😊","Message received ✅"]), status="sent")
    db.add(reply)
    db.commit()
    recent = db.query(Message).order_by(Message.timestamp.desc()).limit(6).all()
    db.close()
    await broadcast({"type":"update","messages":msgs_to_list(reversed(recent)),"stats":get_stats()})
    return {"ok": True}

@app.delete("/api/messages/clear")
async def clear_messages():
    db = SessionLocal()
    db.query(Message).delete()
    db.commit()
    db.close()
    await broadcast({"type":"init","messages":[],"stats":get_stats(),"hourly":get_hourly()})
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
:root{--bg:#080c14;--surface:#0f1623;--card:#131d2e;--border:rgba(0,255,136,0.12);--green:#00ff88;--green-dim:#00994d;--cyan:#00d4ff;--yellow:#ffd600;--red:#ff4466;--purple:#b088ff;--text:#e8f4f0;--muted:#4a6670;--grid:rgba(0,255,136,0.03);}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;}
body{background:var(--bg);color:var(--text);font-family:"Outfit",sans-serif;min-height:100vh;overflow-x:hidden;}
body::before{content:"";position:fixed;inset:0;background-image:linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px);background-size:40px 40px;pointer-events:none;z-index:0;}
header{position:sticky;top:0;z-index:100;background:rgba(8,12,20,0.92);backdrop-filter:blur(20px);border-bottom:1px solid var(--border);padding:1rem 2rem;display:flex;align-items:center;justify-content:space-between;}
.logo{display:flex;align-items:center;gap:.75rem;}
.logo-icon{width:36px;height:36px;background:var(--green);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;animation:pulse 2s ease-in-out infinite;}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(0,255,136,.4);}50%{box-shadow:0 0 0 8px rgba(0,255,136,0);}}
.logo-text{font-family:"Space Mono",monospace;font-size:1.1rem;font-weight:700;color:var(--green);}
.logo-sub{font-size:.65rem;color:var(--muted);letter-spacing:.1em;text-transform:uppercase;}
.header-right{display:flex;align-items:center;gap:1rem;}
.status-pill{display:flex;align-items:center;gap:.5rem;background:rgba(0,255,136,.08);border:1px solid var(--border);border-radius:20px;padding:.4rem 1rem;font-family:"Space Mono",monospace;font-size:.7rem;color:var(--green);}
.status-dot{width:8px;height:8px;background:var(--green);border-radius:50%;animation:blink 1.5s ease-in-out infinite;}
@keyframes blink{0%,100%{opacity:1;}50%{opacity:.3;}}
.time-display{font-family:"Space Mono",monospace;font-size:.75rem;color:var(--muted);}
main{position:relative;z-index:1;padding:2rem;max-width:1400px;margin:0 auto;}
.stats-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:1rem;margin-bottom:2rem;}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:1.5rem;transition:transform .3s,border-color .3s;}
.stat-card:hover{transform:translateY(-3px);border-color:rgba(0,255,136,.25);}
.stat-label{font-size:.7rem;letter-spacing:.15em;text-transform:uppercase;color:var(--muted);margin-bottom:.75rem;font-family:"Space Mono",monospace;}
.stat-value{font-size:2.2rem;font-weight:900;line-height:1;margin-bottom:.4rem;}
.stat-sub{font-size:.7rem;color:var(--muted);}
.stat-sub b{color:var(--green);}
.c-green .stat-value{color:var(--green);}.c-cyan .stat-value{color:var(--cyan);}.c-yellow .stat-value{color:var(--yellow);}.c-red .stat-value{color:var(--red);}.c-purple .stat-value{color:var(--purple);}
.main-grid{display:grid;grid-template-columns:1fr 1.2fr;gap:1.5rem;margin-bottom:1.5rem;}
.panel{background:var(--card);border:1px solid var(--border);border-radius:16px;overflow:hidden;}
.panel-header{display:flex;align-items:center;justify-content:space-between;padding:1.2rem 1.5rem;border-bottom:1px solid var(--border);}
.panel-title{font-family:"Space Mono",monospace;font-size:.8rem;letter-spacing:.1em;text-transform:uppercase;color:var(--green);}
.panel-badge{font-family:"Space Mono",monospace;font-size:.65rem;background:rgba(0,255,136,.1);border:1px solid var(--border);color:var(--green);padding:.2rem .6rem;border-radius:20px;}
.chart-wrap{padding:1.5rem;}
.chart-bars{display:flex;align-items:flex-end;gap:3px;height:140px;margin-bottom:.5rem;}
.bar-col{flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;}
.bar{width:100%;background:linear-gradient(to top,var(--green-dim),var(--green));border-radius:3px 3px 0 0;min-height:4px;cursor:pointer;transition:all .2s;}
.bar:hover{background:linear-gradient(to top,var(--cyan),#88ffee);}
.bar-label{font-family:"Space Mono",monospace;font-size:.5rem;color:var(--muted);}
.chart-legend{display:flex;gap:1.5rem;margin-top:1rem;padding-top:1rem;border-top:1px solid var(--border);}
.legend-item{display:flex;align-items:center;gap:.4rem;font-size:.7rem;color:var(--muted);}
.legend-dot{width:8px;height:8px;border-radius:50%;}
.search-bar{display:flex;gap:.5rem;padding:1rem 1.5rem;border-bottom:1px solid var(--border);}
.search-input{flex:1;background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:8px;padding:.5rem .75rem;color:var(--text);font-family:"Space Mono",monospace;font-size:.75rem;outline:none;}
.search-input:focus{border-color:var(--green);}
.search-btn{background:rgba(0,255,136,.1);border:1px solid var(--border);border-radius:8px;padding:.5rem .75rem;color:var(--green);font-family:"Space Mono",monospace;font-size:.7rem;cursor:pointer;}
.messages-list{padding:1rem;display:flex;flex-direction:column;gap:.6rem;max-height:300px;overflow-y:auto;}
.messages-list::-webkit-scrollbar{width:4px;}
.messages-list::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px;}
.msg-item{display:flex;gap:.75rem;padding:.75rem;border-radius:10px;background:rgba(255,255,255,.02);border:1px solid transparent;transition:all .3s;animation:slideIn .4s ease;}
@keyframes slideIn{from{opacity:0;transform:translateX(-10px);}to{opacity:1;transform:translateX(0);}}
.msg-item:hover{background:rgba(0,255,136,.04);border-color:var(--border);}
.msg-avatar{width:32px;height:32px;min-width:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:.9rem;}
.msg-avatar.received{background:rgba(0,212,255,.15);}.msg-avatar.sent{background:rgba(0,255,136,.15);}
.msg-body{flex:1;min-width:0;}
.msg-from{font-family:"Space Mono",monospace;font-size:.62rem;color:var(--muted);margin-bottom:.2rem;}
.msg-text{font-size:.85rem;color:var(--text);line-height:1.4;}
.msg-status{display:inline-block;font-size:.58rem;padding:.12rem .4rem;border-radius:4px;font-family:"Space Mono",monospace;margin-top:.2rem;}
.msg-status.received{background:rgba(0,212,255,.1);color:var(--cyan);}.msg-status.sent{background:rgba(0,255,136,.1);color:var(--green);}
.msg-time{font-family:"Space Mono",monospace;font-size:.6rem;color:var(--muted);white-space:nowrap;align-self:flex-end;}
.bottom-grid{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:1.5rem;}
.users-list{padding:1rem;max-height:260px;overflow-y:auto;}
.user-row{display:flex;align-items:center;gap:.75rem;padding:.7rem;border-radius:10px;border:1px solid transparent;transition:all .3s;margin-bottom:.4rem;}
.user-row:hover{background:rgba(176,136,255,.04);border-color:rgba(176,136,255,.15);}
.user-avatar{width:32px;height:32px;border-radius:50%;background:rgba(176,136,255,.15);display:flex;align-items:center;justify-content:center;}
.user-phone{font-family:"Space Mono",monospace;font-size:.7rem;color:var(--text);}
.user-meta{font-size:.62rem;color:var(--muted);}
.user-count{font-family:"Space Mono",monospace;font-size:.75rem;color:var(--purple);font-weight:700;}
.workflow-list{padding:1rem;}
.workflow-item{display:flex;align-items:center;gap:1rem;padding:.8rem;border-radius:10px;border:1px solid transparent;margin-bottom:.5rem;transition:all .3s;}
.workflow-item:hover{background:rgba(0,255,136,.03);border-color:var(--border);}
.wf-icon{width:34px;height:34px;min-width:34px;border-radius:8px;display:flex;align-items:center;justify-content:center;}
.wf-info{flex:1;}
.wf-name{font-size:.82rem;font-weight:600;margin-bottom:.15rem;}
.wf-time{font-family:"Space Mono",monospace;font-size:.58rem;color:var(--muted);}
.wf-badge{font-family:"Space Mono",monospace;font-size:.58rem;padding:.18rem .5rem;border-radius:20px;font-weight:700;}
.wf-badge.completed{background:rgba(0,255,136,.1);color:var(--green);border:1px solid rgba(0,255,136,.2);}
.wf-badge.running{background:rgba(255,214,0,.1);color:var(--yellow);border:1px solid rgba(255,214,0,.2);}
.wf-badge.pending{background:rgba(0,212,255,.1);color:var(--cyan);border:1px solid rgba(0,212,255,.2);}
.ctrl-panel{padding:1.2rem;display:flex;flex-direction:column;gap:.75rem;}
.sim-btn{width:100%;padding:.9rem;background:linear-gradient(135deg,var(--green-dim),var(--green));border:none;border-radius:10px;color:#080c14;font-family:"Space Mono",monospace;font-size:.75rem;font-weight:700;cursor:pointer;transition:all .3s;text-transform:uppercase;letter-spacing:.08em;}
.sim-btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,255,136,.3);}
.clear-btn{width:100%;padding:.7rem;background:rgba(255,68,102,.08);border:1px solid rgba(255,68,102,.2);border-radius:10px;color:var(--red);font-family:"Space Mono",monospace;font-size:.7rem;cursor:pointer;transition:all .3s;}
.clear-btn:hover{background:rgba(255,68,102,.15);}
.ws-indicator{display:flex;align-items:center;gap:.5rem;font-family:"Space Mono",monospace;font-size:.62rem;color:var(--muted);padding:.6rem .75rem;background:rgba(0,255,136,.04);border:1px solid var(--border);border-radius:8px;}
.ws-dot{width:6px;height:6px;border-radius:50%;background:var(--red);}
.ws-dot.connected{background:var(--green);animation:blink 1.5s infinite;}
.db-info{padding:.7rem;background:rgba(176,136,255,.05);border:1px solid rgba(176,136,255,.15);border-radius:8px;font-size:.7rem;color:var(--muted);line-height:1.7;}
.db-info strong{color:var(--purple);}
@media(max-width:1100px){.stats-grid{grid-template-columns:repeat(3,1fr);}.main-grid,.bottom-grid{grid-template-columns:1fr;}}
</style>
</head>
<body>
<header>
  <div class="logo">
    <div class="logo-icon">💬</div>
    <div><div class="logo-text">WhatsFlow</div><div class="logo-sub">Dashboard v2.1 — SQLite</div></div>
  </div>
  <div class="header-right">
    <div class="status-pill"><div class="status-dot"></div>Bot Online</div>
    <div class="time-display" id="clock">--:--:--</div>
  </div>
</header>
<main>
  <div class="stats-grid">
    <div class="stat-card c-green"><div class="stat-label">Total Messages</div><div class="stat-value" id="s-total">0</div><div class="stat-sub">Stored in <b>SQLite</b></div></div>
    <div class="stat-card c-cyan"><div class="stat-label">Received</div><div class="stat-value" id="s-received">0</div><div class="stat-sub">Inbound</div></div>
    <div class="stat-card c-yellow"><div class="stat-label">Sent</div><div class="stat-value" id="s-sent">0</div><div class="stat-sub">Bot replies</div></div>
    <div class="stat-card c-red"><div class="stat-label">Failed</div><div class="stat-value" id="s-failed">0</div><div class="stat-sub">Errors</div></div>
    <div class="stat-card c-purple"><div class="stat-label">Users</div><div class="stat-value" id="s-users">0</div><div class="stat-sub">Unique phones</div></div>
  </div>
  <div class="main-grid">
    <div class="panel">
      <div class="panel-header"><div class="panel-title">📊 Hourly Activity</div><div class="panel-badge">24h</div></div>
      <div class="chart-wrap">
        <div class="chart-bars" id="chart-bars"></div>
        <div class="chart-legend">
          <div class="legend-item"><div class="legend-dot" style="background:var(--green)"></div>Messages</div>
          <div class="legend-item"><div class="legend-dot" style="background:var(--cyan)"></div>Peak</div>
        </div>
      </div>
    </div>
    <div class="panel">
      <div class="panel-header"><div class="panel-title">💬 Live Messages</div><div class="panel-badge" id="msg-count">0 total</div></div>
      <div class="search-bar">
        <input class="search-input" id="search-input" placeholder="Search messages or phone numbers..." oninput="searchMessages()"/>
        <button class="search-btn" onclick="searchMessages()">🔍</button>
      </div>
      <div class="messages-list" id="messages-list"></div>
    </div>
  </div>
  <div class="bottom-grid">
    <div class="panel">
      <div class="panel-header"><div class="panel-title">👥 Active Users</div><div class="panel-badge" id="user-count">0</div></div>
      <div class="users-list" id="users-list"></div>
    </div>
    <div class="panel">
      <div class="panel-header"><div class="panel-title">⚡ Workflow</div></div>
      <div class="workflow-list">
        <div class="workflow-item"><div class="wf-icon" style="background:rgba(0,255,136,.1)">🚀</div><div class="wf-info"><div class="wf-name">Bot Engine</div><div class="wf-time">Online</div></div><div class="wf-badge completed">Active</div></div>
        <div class="workflow-item"><div class="wf-icon" style="background:rgba(255,214,0,.1)">🗄️</div><div class="wf-info"><div class="wf-name">SQLite DB</div><div class="wf-time">whatsflow.db</div></div><div class="wf-badge completed">Active</div></div>
        <div class="workflow-item"><div class="wf-icon" style="background:rgba(0,212,255,.1)">🔌</div><div class="wf-info"><div class="wf-name">WebSocket</div><div class="wf-time">Real-time</div></div><div class="wf-badge running" id="wf-ws">Connecting</div></div>
        <div class="workflow-item"><div class="wf-icon" style="background:rgba(176,136,255,.1)">🔗</div><div class="wf-info"><div class="wf-name">Webhook</div><div class="wf-time">/webhook</div></div><div class="wf-badge pending">Pending</div></div>
      </div>
    </div>
    <div class="panel">
      <div class="panel-header"><div class="panel-title">🎮 Controls</div></div>
      <div class="ctrl-panel">
        <div class="ws-indicator"><div class="ws-dot" id="ws-dot"></div><span id="ws-status">Connecting...</span></div>
        <button class="sim-btn" onclick="simulate()">⚡ Simulate Message</button>
        <button class="clear-btn" onclick="clearMessages()">🗑️ Clear All Messages</button>
        <div class="db-info"><strong>SQLite Database</strong><br/>Messages persist across restarts.<br/>File: <code style="color:var(--green)">app/whatsflow.db</code><br/>REST API: <code style="color:var(--cyan)">/api/messages /api/stats /api/users</code></div>
      </div>
    </div>
  </div>
</main>
<script>
function tick(){document.getElementById("clock").textContent=new Date().toLocaleTimeString("de-DE");}
tick();setInterval(tick,1000);
let ws;
function connect(){
  ws=new WebSocket("ws://"+location.host+"/ws");
  ws.onopen=()=>{document.getElementById("ws-dot").classList.add("connected");document.getElementById("ws-status").textContent="WebSocket: Connected ✓";document.getElementById("wf-ws").textContent="Active";document.getElementById("wf-ws").className="wf-badge completed";};
  ws.onclose=()=>{document.getElementById("ws-dot").classList.remove("connected");document.getElementById("ws-status").textContent="Reconnecting...";setTimeout(connect,3000);};
  ws.onmessage=e=>{const d=JSON.parse(e.data);if(d.type==="init"){updateStats(d.stats);renderMessages(d.messages);renderChart(d.hourly);loadUsers();}else if(d.type==="update"){updateStats(d.stats);renderMessages(d.messages,true);loadUsers();}};
}
connect();
function animCount(el,target){let v=parseInt(el.textContent)||0;const t=setInterval(()=>{v=Math.min(v+Math.max(1,Math.ceil((target-v)/10)),target);el.textContent=v;if(v>=target)clearInterval(t);},40);}
function updateStats(s){animCount(document.getElementById("s-total"),s.total);animCount(document.getElementById("s-received"),s.received);animCount(document.getElementById("s-sent"),s.sent);animCount(document.getElementById("s-failed"),s.failed);animCount(document.getElementById("s-users"),s.users);document.getElementById("msg-count").textContent=s.total+" total";}
function renderMessages(msgs,append=false){
  const list=document.getElementById("messages-list");
  if(!append)list.innerHTML="";
  msgs.forEach(m=>{const div=document.createElement("div");div.className="msg-item";div.innerHTML=`<div class="msg-avatar ${m.status}">${m.from==="Bot"?"🤖":"👤"}</div><div class="msg-body"><div class="msg-from">${m.from}</div><div class="msg-text">${m.text}</div><span class="msg-status ${m.status}">${m.status}</span></div><div class="msg-time">${m.time}</div>`;list.appendChild(div);});
  list.scrollTop=list.scrollHeight;
}
let searchTimer;
function searchMessages(){clearTimeout(searchTimer);searchTimer=setTimeout(async()=>{const q=document.getElementById("search-input").value;const res=await fetch(`/api/messages?search=${encodeURIComponent(q)}&limit=50`);renderMessages(await res.json());},300);}
function renderChart(hourly){const max=Math.max(...hourly,1);const container=document.getElementById("chart-bars");container.innerHTML="";hourly.forEach((val,i)=>{const pct=(val/max)*100;const isMax=val===max&&val>0;const col=document.createElement("div");col.className="bar-col";col.innerHTML=`<div class="bar" style="height:${Math.max(pct,3)}%;${isMax?"background:linear-gradient(to top,var(--cyan),#88ffee);":""}" title="${val} msgs at ${i}:00"></div><div class="bar-label">${i%4===0?i:""}</div>`;container.appendChild(col);});}
async function loadUsers(){const res=await fetch("/api/users");const users=await res.json();document.getElementById("user-count").textContent=users.length+" users";const list=document.getElementById("users-list");list.innerHTML="";users.forEach(u=>{const div=document.createElement("div");div.className="user-row";div.innerHTML=`<div class="user-avatar">👤</div><div class="user-info"><div class="user-phone">${u.phone}</div><div class="user-meta">Last: ${u.last_seen.substring(11)}</div></div><div class="user-count">${u.messages} msgs</div>`;list.appendChild(div);});}
async function simulate(){const btn=document.querySelector(".sim-btn");btn.textContent="⏳ Sending...";btn.disabled=true;await fetch("/simulate",{method:"POST"});setTimeout(()=>{btn.textContent="⚡ Simulate Message";btn.disabled=false;},800);}
async function clearMessages(){if(!confirm("Clear all messages from database?"))return;await fetch("/api/messages/clear",{method:"DELETE"});}
</script>
</body>
</html>
'''
