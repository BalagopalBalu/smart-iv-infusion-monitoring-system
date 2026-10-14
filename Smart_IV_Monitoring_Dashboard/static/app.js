const $ = (id) => document.getElementById(id);
let latestEvents = [];
let dropPoints = [];
let weightPoints = [];
let configLoaded = false;

function timeLabel(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit", second:"2-digit"});
}
function shortTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"});
}
function setDot(id, good) {
  const el = $(id); el.classList.remove("good","bad");
  el.classList.add(good ? "good" : "bad");
}
function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
async function getJSON(url, options={}) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}
function renderAlerts(alerts) {
  const list = $("alertsList");
  if (!alerts || !alerts.length) {
    list.innerHTML = '<div class="empty-state">No alerts recorded yet. System events will appear here.</div>';
    $("alertCount").textContent = "0 alerts"; return;
  }
  const actual = alerts.filter(e => e.kind === "alert");
  $("alertCount").textContent = `${actual.length} alert${actual.length===1?"":"s"}`;
  list.innerHTML = alerts.slice(0,8).map(e => {
    const cls = e.kind === "drop" ? "drop" : (e.kind === "system" ? "system" : "");
    const icon = e.kind === "alert" ? "!" : (e.kind === "drop" ? "↘" : (e.kind === "relay" ? "⇄" : "✓"));
    return `<div class="alert-item"><div class="alert-icon ${cls}">${icon}</div><div><strong>${escapeHtml(e.message)}</strong><small>${timeLabel(e.time)} · ${escapeHtml(e.kind)}</small></div></div>`;
  }).join("");
}
function renderHistory(events) {
  const body = $("historyBody");
  if (!events || !events.length) {
    body.innerHTML = '<tr><td colspan="4" class="empty-cell">No events recorded yet.</td></tr>'; return;
  }
  body.innerHTML = events.slice(0,80).map(e => {
    const kind = escapeHtml(e.kind || "event");
    const value = e.value === null || e.value === undefined ? "—" : escapeHtml(e.value);
    return `<tr><td>${timeLabel(e.time)}</td><td><span class="type-chip ${kind.toLowerCase()}">${kind}</span></td><td>${escapeHtml(e.message)}</td><td>${value}</td></tr>`;
  }).join("");
}
function drawChart(canvasId, points, opts={}) {
  const canvas = $(canvasId);
  if (!canvas) return;
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const w = Math.max(260, rect.width), h = Math.max(160, rect.height);
  canvas.width = w*dpr; canvas.height = h*dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr,dpr);
  ctx.clearRect(0,0,w,h);
  const pad = {l:42,r:12,t:14,b:28};
  const cw=w-pad.l-pad.r, ch=h-pad.t-pad.b;
  ctx.font = "10px system-ui"; ctx.fillStyle="#8ba0af"; ctx.strokeStyle="#edf2f6"; ctx.lineWidth=1;
  const vals = points.map(p=>Number(p.v)).filter(Number.isFinite);
  let min = opts.min ?? (vals.length ? Math.min(...vals) : 0);
  let max = opts.max ?? (vals.length ? Math.max(...vals) : 5);
  if (max === min) { max += 1; min = Math.max(opts.min ?? 0, min - 1); }
  if (opts.min === undefined) min = Math.max(0, min - (max-min)*.12);
  max += (max-min)*.12;
  for(let i=0;i<5;i++){
    const y=pad.t+ch*i/4;
    ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(w-pad.r,y);ctx.stroke();
    const val=max-(max-min)*i/4;
    ctx.textAlign="right";ctx.fillText(Number(val.toFixed(1)).toString(),pad.l-8,y+3);
  }
  if (!points.length) {
    ctx.textAlign="center";ctx.fillStyle="#9aabb7";ctx.fillText(opts.empty || "Waiting for telemetry",w/2,h/2);
    return;
  }
  const color=opts.color||"#368fd0";
  const xAt=i=>pad.l+(points.length===1?cw/2:i*cw/(points.length-1));
  const yAt=v=>pad.t+ch-(Number(v)-min)/(max-min)*ch;
  ctx.beginPath();
  points.forEach((p,i)=>{const x=xAt(i),y=yAt(p.v);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);});
  ctx.strokeStyle=color;ctx.lineWidth=2.3;ctx.lineJoin="round";ctx.lineCap="round";ctx.stroke();
  points.forEach((p,i)=>{ctx.beginPath();ctx.arc(xAt(i),yAt(p.v),3,0,Math.PI*2);ctx.fillStyle="#fff";ctx.fill();ctx.strokeStyle=color;ctx.lineWidth=2;ctx.stroke();});
  ctx.textAlign="center";ctx.fillStyle="#8ba0af";
  const labels=[0,Math.floor((points.length-1)/2),points.length-1].filter((v,i,a)=>a.indexOf(v)===i);
  labels.forEach(i=>ctx.fillText(points[i].t||"",xAt(i),h-8));
}
function redrawCharts() {
  drawChart("dropChart",dropPoints,{color:"#368fd0",min:0,empty:"Drop events will appear here"});
  drawChart("weightChart",weightPoints,{color:"#29afc7",min:0,empty:"Waiting for UNO weight telemetry"});
}
function applyCamera(url) {
  const img=$("cameraImage"), empty=$("cameraEmpty");
  if (url && /^https?:\/\//i.test(url)) {
    if (img.src !== url) img.src = url;
    img.hidden=false; empty.hidden=true;
    img.onerror=()=>{img.hidden=true;empty.hidden=false;empty.querySelector("strong").textContent="Stream could not be loaded";empty.querySelector("p").textContent="Check that the camera URL is correct and reachable from this laptop. The serial relay can still operate independently.";};
    img.onload=()=>{img.hidden=false;empty.hidden=true;};
  } else {
    img.removeAttribute("src");img.hidden=true;empty.hidden=false;
  }
}
async function refresh() {
  try {
    const [s, ev] = await Promise.all([getJSON("/api/state"), getJSON("/api/events")]);
    $("dropCount").textContent=s.drop_count ?? "—";
    $("chartCurrentCount").textContent=s.drop_count ?? "—";
    $("weightValue").textContent=s.weight_g == null ? "—" : Number(s.weight_g).toFixed(1);
    $("infusionStatus").textContent=s.weight_status || "WAITING";
    $("thresholdText").textContent=`Low-weight threshold: ${Number(s.low_weight_limit_g || 150).toFixed(0)} g`;
    const badge=$("weightBadge"); badge.textContent=s.weight_g == null ? "Awaiting telemetry" : (String(s.weight_status).includes("LOW") || String(s.weight_status).includes("ALERT") ? "Check IV level" : "Telemetry received");
    badge.className="status-badge "+(s.weight_g==null?"neutral":((String(s.weight_status).includes("LOW")||String(s.weight_status).includes("ALERT"))?"warn":"good"));
    $("systemStatus").textContent=s.system_status || "—";
    $("lastUpdated").textContent=`Updated ${timeLabel(s.last_update)}`;
    const good=s.system_status==="RUNNING";
    $("systemDot").className="state-dot "+(good?"good":(String(s.system_status).includes("ERROR")?"bad":""));
    $("espStatus").textContent=s.esp_status || "Disconnected";
    $("unoStatus").textContent=s.uno_status || "Disconnected";
    setDot("espDot",String(s.esp_status).startsWith("Connected"));
    setDot("unoDot",String(s.uno_status).startsWith("Connected"));
    $("lastDrop").textContent=s.last_drop_at?`Last event ${timeLabel(s.last_drop_at)}`:"Waiting for first drop event";
    $("eventTotal").textContent=s.event_count ?? ev.length;
    applyCamera(s.camera_url || $("cameraUrl").value);
    if (!configLoaded) {
      $("espPort").value = s.config?.esp_port || "COM7";
      $("unoPort").value = s.config?.uno_port || "COM4";
      $("cameraUrl").value = s.camera_url || "";
      $("weightLimit").value = s.low_weight_limit_g ?? 150;
      configLoaded=true;
    }
    latestEvents=ev;
    renderHistory(ev);
    renderAlerts(ev.filter(e=>["alert","drop","system"].includes(e.kind)).slice(0,30));
    // Keep recent samples from event stream. Weight is plotted when telemetry is received.
    const drops=ev.filter(e=>e.kind==="drop" && Number.isFinite(Number(e.value))).slice(-30);
    dropPoints=drops.map(e=>({t:shortTime(e.time),v:Number(e.value)}));
    if (s.weight_g != null) {
      const last=weightPoints[weightPoints.length-1];
      if (!last || last.v !== Number(s.weight_g) || last.t !== shortTime(s.last_update)) {
        weightPoints.push({t:shortTime(s.last_update),v:Number(s.weight_g)});
        weightPoints=weightPoints.slice(-30);
      }
    }
    redrawCharts();
    if (s.error) $("settingsMessage").textContent="Serial: "+s.error;
  } catch(err) {
    $("systemStatus").textContent="Dashboard API unavailable";
    $("settingsMessage").textContent=err.message;
  }
}
$("saveSettings").addEventListener("click", async()=>{
  const payload={esp_port:$("espPort").value.trim(),uno_port:$("unoPort").value.trim(),camera_url:$("cameraUrl").value.trim(),low_weight_limit_g:Number($("weightLimit").value)};
  try{
    await getJSON("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    $("settingsMessage").textContent="Saved. Restart the app to apply changed serial ports.";
    applyCamera(payload.camera_url);
  }catch(e){$("settingsMessage").textContent="Could not save: "+e.message;}
});
$("openCamera").addEventListener("click",()=>{
  const url=$("cameraUrl").value.trim();
  if(url) window.open(url,"_blank","noopener");
  else $("settingsMessage").textContent="Enter and save the camera stream URL first.";
});
$("resetCount").addEventListener("click",async()=>{
  if(confirm("Reset the dashboard display count? This does not reset the ESP32-CAM's internal counter.")){
    await getJSON("/api/reset-count",{method:"POST"}); refresh();
  }
});
$("refreshHistory").addEventListener("click",refresh);
$("clock").textContent=new Date().toLocaleTimeString();
setInterval(()=>$("clock").textContent=new Date().toLocaleTimeString(),1000);
window.addEventListener("resize",redrawCharts);
refresh();
setInterval(refresh,1500);
