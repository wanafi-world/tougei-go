// 陶芸でGO — 家族でつながるセーブ（Firebase Realtime Database）と「新しいゲームがあるよ」ボタン。
// ゲーム本体からは window.TG を使う。このファイルがない・設定がないときは window.TG.on = false で、
// ゲームはこれまでどおり この iPad の中だけにセーブする。
//
// データの形：
//   fam/<家族ID>/m/<sid> = { name, day, money, rep, hero, savedAt, v, del? }   ← 一覧用の小さい情報
//   fam/<家族ID>/s/<sid> = { json, savedAt, v }                                 ← セーブ全体（JSON 文字列）
(function(){
  'use strict';
  const FAM_KEY = 'tougei_family';
  const SALT = 'tougei-family:';
  const MAX_LEN = 9000000; // Firebase の文字の上限(10MB)より少し小さく
  const DEBOUNCE = 15000;
  const cfg = window.FIREBASE_CONFIG;
  let rtdb = null;
  try{
    if(cfg && cfg.databaseURL && window.firebase){ firebase.initializeApp(cfg); rtdb = firebase.database(); }
  }catch(e){ console.warn('firebase init failed', e); rtdb = null; }

  // ---------- 小さな道具 ----------
  async function sha256(s){
    const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
    return Array.from(new Uint8Array(b)).map(x=>x.toString(16).padStart(2,'0')).join('');
  }
  const norm = s => String(s||'').normalize('NFKC').trim().replace(/\s+/g,'').toLowerCase();
  const withTimeout = (p, ms) => new Promise((res, rej)=>{
    const t = setTimeout(()=>rej(new Error('timeout')), ms);
    p.then(v=>{ clearTimeout(t); res(v); }, e=>{ clearTimeout(t); rej(e); });
  });
  const newSid = () => 'p' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const hhmm = t => { const d = new Date(t); return (d.getMonth()+1) + '/' + d.getDate() + ' ' + d.getHours() + ':' + String(d.getMinutes()).padStart(2,'0'); };

  // ---------- 家族のあいことば ----------
  function askFamily(){
    return new Promise(res=>{
      const ov = document.createElement('div');
      ov.id = 'famOv';
      ov.style.cssText = 'position:fixed;inset:0;z-index:200;display:flex;align-items:center;justify-content:center;padding:16px;background:rgba(10,14,17,.72)';
      ov.innerHTML = '<div class="panel" style="width:min(480px,100%);text-align:center;background:var(--panel,#212e35);border:1px solid var(--line,#3a4d57);border-radius:18px;padding:20px">'+
        '<h2 style="font-family:var(--display);margin:0 0 8px">家族のあいことば</h2>'+
        '<p style="font-size:16px;line-height:1.6;margin:0 0 12px">家族の iPad どうしで、セーブをつなぐための「あいことば」を入れてね。<br><b>どの iPad にも同じあいことば</b>を入れると、同じセーブで遊べるよ。<br><small style="color:var(--muted,#a3b3b8)">（6文字以上。家族だけが知っている言葉にしてね。あとから最初の画面で変えられるよ）</small></p>'+
        '<input id="famIn" type="text" maxlength="60" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" style="font-size:20px;padding:10px 12px;border-radius:12px;border:2px solid var(--line,#3a4d57);background:var(--bg,#172126);color:var(--ink,#eef2ef);width:min(100%,360px);-webkit-user-select:text;user-select:text;touch-action:auto">'+
        '<div id="famMsg" style="color:var(--bad,#e46a5f);font-weight:bold;min-height:24px;margin-top:6px"></div>'+
        '<div class="row" style="justify-content:center;gap:10px;flex-wrap:wrap"><button class="primary" id="famOk">これにする</button><button id="famSkip">あとで（この iPad だけにセーブ）</button></div></div>';
      document.body.appendChild(ov);
      const inp = ov.querySelector('#famIn'), msg = ov.querySelector('#famMsg');
      ['keydown','keyup','keypress','pointerdown','touchstart'].forEach(t=>inp.addEventListener(t,e=>e.stopPropagation()));
      ov.querySelector('#famOk').onclick = ()=>{
        const v = norm(inp.value);
        if(v.length < 6){ msg.textContent = '6文字以上にしてね'; return; }
        try{ localStorage.setItem(FAM_KEY, v); }catch(e){}
        ov.remove(); res(v);
      };
      ov.querySelector('#famSkip').onclick = ()=>{ ov.remove(); res(null); };
      setTimeout(()=>{ try{ inp.focus(); }catch(e){} }, 50);
    });
  }
  let famP = null;
  function ready(){
    if(!rtdb) return Promise.resolve(null);
    if(!famP) famP = (async()=>{
      let v = null; try{ v = localStorage.getItem(FAM_KEY); }catch(e){}
      if(!v) v = await askFamily();
      if(!v){ setStatus('skip'); return null; }
      return await sha256(SALT + v);
    })();
    return famP;
  }
  function changeFamily(){
    flush().finally(()=>{ try{ localStorage.removeItem(FAM_KEY); }catch(e){} location.reload(); });
  }

  // ---------- ようす（最初の画面に出す） ----------
  let st = { s: rtdb ? 'wait0' : 'off', at: 0 };
  const listeners = [];
  function setStatus(s, at){ st = { s, at: at || st.at }; listeners.forEach(f=>{ try{ f(st); }catch(e){} }); renderSec(); }
  function statusText(){
    switch(st.s){
      case 'off':  return 'この iPad の中だけにセーブしているよ。';
      case 'skip': return 'この iPad の中だけにセーブしているよ（あいことばがまだだよ）。';
      case 'wait0':return '家族のセーブにつないでいるよ…';
      case 'ok':   return st.at ? '家族のセーブにつながっているよ（' + hhmm(st.at) + ' に送ったよ）' : '家族のセーブにつながっているよ。';
      case 'send': return 'セーブを送っているよ…';
      case 'err':  return 'いまは送れなかったよ。あとでもう一度送るね。';
      case 'big':  return 'セーブが大きすぎて送れないよ。店の器を売ってみてね。';
    }
    return '';
  }

  // ---------- 一覧・読みこみ・送る・消す ----------
  const cloudAt = {};   // sid -> クラウドにある savedAt（わかっているもの）
  async function list(){
    const fid = await ready(); if(!fid) return null;
    try{
      const s = await withTimeout(rtdb.ref('fam/' + fid + '/m').get(), 15000);
      const out = {}; s.forEach(c => { const v = c.val(); if(v && typeof v === 'object'){ out[c.key] = v; cloudAt[c.key] = v.savedAt || 0; } });
      if(st.s === 'wait0' || st.s === 'err') setStatus('ok');
      return out;
    }catch(e){ console.warn('list failed', e); setStatus('err'); return null; }
  }
  async function get(sid){
    const fid = await ready(); if(!fid) return null;
    try{
      const s = await withTimeout(rtdb.ref('fam/' + fid + '/s/' + sid).get(), 20000);
      const v = s.val(); if(!v || !v.json) return null;
      const o = JSON.parse(v.json); o.sid = sid; o.savedAt = o.savedAt || v.savedAt || 0;
      cloudAt[sid] = o.savedAt;
      return o;
    }catch(e){ console.warn('get failed', e); setStatus('err'); return null; }
  }
  const metaOf = o => ({ name: String(o.name||''), day: o.day||1, money: o.money||0, rep: o.rep||0, hero: o.hero||'m', savedAt: o.savedAt||0, v: 1 });
  const dirty = new Map();   // sid -> セーブのオブジェクト（送る直前に文字にする）
  let timer = null, sending = null;
  function queue(o, now){
    if(!rtdb || !o || o.stub) return;
    if(!o.sid) o.sid = newSid();
    if(!o.savedAt) o.savedAt = Date.now();
    if(cloudAt[o.sid] === o.savedAt) return;
    dirty.set(o.sid, o);
    if(now) return flush();
    if(!timer) timer = setTimeout(()=>{ timer = null; flush(); }, DEBOUNCE);
  }
  function flush(){
    if(timer){ clearTimeout(timer); timer = null; }
    if(!rtdb || !dirty.size) return Promise.resolve();
    if(sending) return sending.then(()=>flush());
    sending = (async()=>{
      const fid = await ready(); if(!fid){ dirty.clear(); return; }
      const items = [...dirty.values()]; dirty.clear();
      const up = {};
      for(const o of items){
        if(cloudAt[o.sid] === o.savedAt) continue;
        let json; try{ json = JSON.stringify(o); }catch(e){ continue; }
        if(json.length > MAX_LEN){ setStatus('big'); continue; }
        up['s/' + o.sid] = { json, savedAt: o.savedAt, v: 1 };
        up['m/' + o.sid] = metaOf(o);
      }
      if(!Object.keys(up).length) return;
      setStatus('send');
      try{
        await withTimeout(rtdb.ref('fam/' + fid).update(up), 20000);
        for(const k in up) if(k[0] === 'm') cloudAt[k.slice(2)] = up[k].savedAt;
        setStatus('ok', Date.now());
      }catch(e){
        console.warn('save failed', e);
        for(const o of items) if(!dirty.has(o.sid) && cloudAt[o.sid] !== o.savedAt) dirty.set(o.sid, o);
        setStatus('err');
        if(!timer) timer = setTimeout(()=>{ timer = null; flush(); }, 30000);
      }
    })().finally(()=>{ sending = null; });
    return sending;
  }
  async function remove(sid){
    if(!rtdb || !sid) return;
    dirty.delete(sid);
    const fid = await ready(); if(!fid) return;
    const at = Date.now();
    try{
      await withTimeout(rtdb.ref('fam/' + fid).update({ ['s/' + sid]: null, ['m/' + sid]: { del: true, savedAt: at, v: 1 } }), 20000);
      cloudAt[sid] = at;
    }catch(e){ console.warn('remove failed', e); setStatus('err'); }
  }
  const synced = (sid, at) => !!sid && cloudAt[sid] === at;

  // アプリをとじる・ほかのアプリにかえる瞬間に、すぐ送る（iPad ではここが大事）
  document.addEventListener('visibilitychange', ()=>{ if(document.visibilityState === 'hidden') flush(); });
  window.addEventListener('pagehide', ()=>{ flush(); });

  // ---------- 最初の画面の「家族のセーブ」らん ----------
  const META = document.querySelector('meta[name="tougei-build"]');
  const BUILD = META ? META.content : '';
  function renderSec(){
    const sec = document.getElementById('cloudSec'); if(!sec) return;
    const famBtn = !rtdb ? '' : (st.s === 'skip'
      ? '<button id="famChange" style="font-size:14px;min-height:36px">あいことばを入れる</button>'
      : '<button id="famChange" style="font-size:14px;min-height:36px">あいことばを変える</button>');
    const updBtn = BUILD ? '<button id="updNow" style="font-size:14px;min-height:36px">ゲームを新しくする</button>' : '';
    sec.innerHTML = '<p class="muted" style="font-size:13px;margin:0 0 6px">' + statusText() + '</p>' +
      '<div class="row" style="justify-content:center;gap:8px;flex-wrap:wrap">' + famBtn + updBtn + '</div>' +
      (BUILD ? '<p class="muted" style="font-size:11px;margin:4px 0 0;opacity:.7">ばんごう ' + BUILD + '</p>' : '');
    const f = sec.querySelector('#famChange');
    if(f) f.onclick = () => {
      if(f.dataset.armed || st.s === 'skip') changeFamily();
      else { f.dataset.armed = '1'; f.textContent = 'もう一度おすと変えられるよ'; }
    };
    const u = sec.querySelector('#updNow'); if(u) u.onclick = () => saveThenReload(newV);
  }

  // ---------- 新しいゲームがあるよ（version.json と比べる） ----------
  let shown = false, newV = '';
  function saveThenReload(v){
    const b = document.getElementById('tgUpd'); if(b){ b.textContent = 'セーブしてから新しくしているよ…'; b.disabled = true; }
    try{ window.dispatchEvent(new Event('tougei-save-now')); }catch(e){}
    const go = () => location.replace(location.pathname + '?v=' + encodeURIComponent(v || Date.now().toString(36)));
    withTimeout(flush(), 8000).then(go, go);
  }
  function showBtn(){
    if(shown) return; shown = true;
    const b = document.createElement('button');
    b.id = 'tgUpd'; b.className = 'primary';
    b.style.cssText = 'position:fixed;left:50%;top:calc(8px + env(safe-area-inset-top,0px));transform:translateX(-50%);z-index:150;padding:8px 18px;font-size:16px;box-shadow:0 4px 14px rgba(0,0,0,.4)';
    b.textContent = '新しいゲームがあるよ・タップで新しくする';
    b.onclick = () => saveThenReload(newV);
    document.body.appendChild(b);
  }
  async function check(){
    if(!BUILD) return;
    try{
      const j = await fetch('version.json?t=' + Date.now(), { cache: 'no-store' }).then(r => r.json());
      if(j && j.v && j.v !== BUILD){ newV = j.v; showBtn(); }
    }catch(e){}
  }
  document.addEventListener('visibilitychange', () => { if(document.visibilityState === 'visible') check(); });
  setInterval(check, 5 * 60 * 1000);
  setTimeout(check, 8000);

  window.TG = { on: !!rtdb, ready, list, get, queue, flush, remove, synced, newSid, changeFamily, renderSec, status: () => st, onStatus: f => listeners.push(f) };
})();
