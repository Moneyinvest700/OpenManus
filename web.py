import json, os, signal, subprocess, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit

key=Path('/run/secrets/gemini_key').read_text().strip()
model=os.environ.get('GEMINI_MODEL','gemini-3.5-flash-lite')
Path('config/config.toml').write_text('[llm]\nmodel='+json.dumps(model)+'\nbase_url="https://generativelanguage.googleapis.com/v1beta/openai/"\napi_key='+json.dumps(key)+'\nmax_tokens=4096\ntemperature=0.2\n[browser]\nheadless=true\ndisable_security=false\n')
del key
lock=threading.Lock()
proc=None
output='Ready. Each run is limited to 8 steps and 5 minutes. One run at a time.'
status='idle'
PAGE='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OpenManus | Abhay</title><style>body{background:#0b1220;color:#e5eaf3;font:16px system-ui;margin:0}main{max-width:900px;margin:50px auto;padding:24px}h1{font-size:38px;margin:8px 0}small{color:#9eacc4}textarea{box-sizing:border-box;width:100%;height:130px;background:#151f32;color:white;border:1px solid #36435e;border-radius:12px;padding:16px;font:16px system-ui;margin-top:24px}button{border:0;border-radius:9px;padding:12px 20px;margin:12px 8px 12px 0;background:#80a9ff;font-weight:700;cursor:pointer}#stop{background:#26334b;color:white}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#111b2d;border:1px solid #2c3a55;padding:20px;border-radius:12px;min-height:180px;font:13px/1.6 monospace}#s{color:#9eccab}</style><main><small>PRIVATE WORKSPACE / GEMINI FREE TIER</small><h1>OpenManus</h1><p>Tell your agent what to work on.</p><small>Python, files and browser tools run inside a separate container. No access to your Hostinger files or other apps. Free API quotas apply. Do not enter passwords or private keys.</small><textarea id="p" placeholder="Apna task Hindi ya English mein likho..."></textarea><div><button id="run">Run task</button><button id="stop">Stop</button><span id="s">Loading...</span></div><pre id="o"></pre><small>8 steps per task / 5 minute timeout / one active task</small></main><script>const p=document.getElementById("p"),o=document.getElementById("o"),s=document.getElementById("s"),run=document.getElementById("run"),stop=document.getElementById("stop");async function call(path,body){let r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok)throw Error(await r.text());return r.json()}run.onclick=async()=>{try{await call('/run',{prompt:p.value});await poll()}catch(e){s.textContent=e.message}};stop.onclick=async()=>{await call('/stop',{});await poll()};async function poll(){try{let r=await fetch('/status');let d=await r.json();o.textContent=d.output;s.textContent=d.status;run.disabled=d.status==='running'}catch(e){s.textContent='Connection lost'}}poll();setInterval(poll,2500)</script></html>'''

def worker(prompt):
 global proc,output,status
 with lock:
  output='Starting OpenManus...\n';status='running'
  proc=subprocess.Popen(['python','-u','web_run.py',prompt],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
  p=proc
 timer=threading.Timer(300,lambda:kill(p));timer.start()
 try:
  for line in iter(p.stdout.readline,b''):
   with lock:output=(output+line.decode(errors='replace'))[-50000:]
  p.wait()
 finally:
  timer.cancel()
  with lock:status='finished' if p.returncode==0 else 'stopped / error';proc=None

def kill(p):
 if p and p.poll() is None:
  try:os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError:pass

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def reply(self,code,data,kind='application/json'):
  b=(json.dumps(data) if kind=='application/json' else data).encode();self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(b)
 def do_GET(self):
  if self.path=='/':self.reply(200,PAGE,'text/html; charset=utf-8')
  elif self.path=='/status':self.reply(200,{'status':status,'output':output})
  else:self.reply(404,{'error':'Not found'})
 def do_POST(self):
  global status
  origin=self.headers.get('Origin')
  if origin and urlsplit(origin).netloc!=self.headers.get('Host'):return self.reply(403,{'error':'Origin rejected'})
  try:
   n=int(self.headers.get('Content-Length','0'))
   if n>16000:raise ValueError()
   data=json.loads(self.rfile.read(n))
  except Exception:return self.reply(400,{'error':'Invalid request'})
  if self.path=='/stop':kill(proc);return self.reply(200,{'ok':True})
  if self.path!='/run':return self.reply(404,{})
  prompt=data.get('prompt','').strip()
  if not prompt or len(prompt)>10000:return self.reply(400,{'error':'Enter a task under 10,000 characters'})
  with lock:
   if status=='running' or status=='starting':return self.reply(409,{'error':'A task is already running'})
   status='starting'
  threading.Thread(target=worker,args=(prompt,),daemon=True).start();self.reply(200,{'ok':True})
ThreadingHTTPServer(('0.0.0.0',8765),Handler).serve_forever()
