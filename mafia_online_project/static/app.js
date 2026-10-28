const tg = window.Telegram?.WebApp;
tg?.ready(); tg?.expand();
const $ = id => document.getElementById(id);
let me = {telegram_id: 0, username: ""}, roomCode = "", hostId = 0, state = null;
function identity(){
  const u = tg?.initDataUnsafe?.user;
  const stored = localStorage.getItem("mafia_user");
  if(u){ me.telegram_id = u.id; me.username = u.first_name || u.username || "O'yinchi"; }
  else if(stored){ me = JSON.parse(stored); }
  else { me.telegram_id = Math.floor(100000 + Math.random()*900000); me.username = "O'yinchi" + me.telegram_id.toString().slice(-3); localStorage.setItem("mafia_user",JSON.stringify(me)); }
  $("username").value = me.username;
}
identity();
function notify(msg){$("notice").textContent=msg;$("notice").classList.remove("hidden");setTimeout(()=>$("notice").classList.add("hidden"),4500)}
async function api(path, data=null){
 const opts={headers:{"Content-Type":"application/json"}};
 if(data){opts.method="POST";opts.body=JSON.stringify(data)}
 const r=await fetch(path,opts);let out={};try{out=await r.json()}catch{}
 if(!r.ok) throw new Error(out.detail||"Xatolik yuz berdi");return out;
}
function payload(){me.username=$("username").value.trim()||me.username;localStorage.setItem("mafia_user",JSON.stringify(me));return me}
$("create").onclick=async()=>{try{payload();const r=await api("/api/rooms",{...me});roomCode=r.code;hostId=me.telegram_id;showLobby();await refresh()}catch(e){notify(e.message)}};
$("join").onclick=async()=>{try{payload();const code=$("roomcode").value.trim().toUpperCase();await api("/api/rooms/join",{...me,code});roomCode=code;showLobby();await refresh()}catch(e){notify(e.message)}};
function showLobby(){$("home").classList.add("hidden");$("lobby").classList.remove("hidden");$("game").classList.add("hidden");$("code").textContent=roomCode}
function showGame(){$("home").classList.add("hidden");$("lobby").classList.add("hidden");$("game").classList.remove("hidden")}
$("copy").onclick=async()=>{try{await navigator.clipboard.writeText(roomCode);notify("Xona kodi nusxalandi")}catch{notify("Xona kodi: "+roomCode)}};
$("start").onclick=async()=>{try{await api("/api/rooms/start",{...me,code:roomCode});await refresh()}catch(e){notify(e.message)}};
$("refresh").onclick=refresh;$("refreshgame").onclick=refresh;
async function refresh(){
 if(!roomCode)return;
 try{state=await api(`/api/rooms/${roomCode}?telegram_id=${me.telegram_id}`);
 const room=state.room;hostId=room.host_id;
 $("code").textContent=roomCode;$("count").textContent=state.players.length+"/15";
 $("players").innerHTML=state.players.map(p=>`<div class="player"><span class="name">${escapeHtml(p.username)}${p.telegram_id===hostId?' <span class="tag">BOSHLIQ</span>':''}</span><span class="tag">${p.alive?'TAYYOR':'CHIQQAN'}</span></div>`).join("");
 if(room.status==="playing"||room.status==="finished"){showGame();renderGame()}else showLobby();
 }catch(e){notify(e.message)}
}
function renderGame(){
 const roleNames={mafia:"MAFIA",doctor:"DOKTOR",detective:"DETEKTIV",citizen:"TINCH AHOLI"};
 const hints={mafia:"Tunda maxfiy harakat qiling. Boshqa rollaringizni oshkor qilmang.",doctor:"Har tun bir o‘yinchini himoya qilish vazifasi bor.",detective:"Gumondorni tekshirish orqali ma’lumot to‘plang.",citizen:"Muhokamada qatnashing va mafiyani ovoz bilan toping."};
 $("role").textContent=roleNames[state.me.role]||"ROL KUTILMOQDA";
 $("rolehint").textContent=hints[state.me.role]||"Rolingiz maxfiy saqlanadi.";
 $("phase").textContent=state.room.phase==="night"?"TUN 🌙":state.room.phase==="day"?"KUN ☀️":"TUGADI";
 $("round").textContent=state.room.round_no+"-raund";
 $("targets").innerHTML=state.players.map(p=>`<div class="player"><span class="name">${escapeHtml(p.username)}${p.telegram_id===me.telegram_id?' (Siz)':''}</span><span class="tag">${p.alive?'TIRIK':'CHIQQAN'}</span>${p.alive&&p.telegram_id!==me.telegram_id&&state.room.phase==='day'?`<button class="vote" data-id="${p.telegram_id}">Ovoz</button>`:''}</div>`).join("");
 document.querySelectorAll(".vote").forEach(b=>b.onclick=async()=>{try{await api("/api/vote",{...me,code:roomCode,target_id:Number(b.dataset.id)});notify("Ovozingiz qabul qilindi");}catch(e){notify(e.message)}});
 $("chat").innerHTML=state.messages.map(m=>`<div class="chatline"><b>${escapeHtml(m.username)}</b>${escapeHtml(m.body)}</div>`).join("");$("chat").scrollTop=$("chat").scrollHeight;
 $("nextphase").style.display=me.telegram_id===hostId?"block":"none";
}
$("nextphase").onclick=async()=>{try{await api("/api/rooms/next-phase",{...me,code:roomCode});await refresh()}catch(e){notify(e.message)}};
$("send").onclick=sendMessage;$("message").addEventListener("keydown",e=>{if(e.key==="Enter")sendMessage()});
async function sendMessage(){const body=$("message").value.trim();if(!body)return;try{await api("/api/chat",{...me,code:roomCode,body});$("message").value="";await refresh()}catch(e){notify(e.message)}}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
setInterval(()=>{if(roomCode)refresh()},5000);
