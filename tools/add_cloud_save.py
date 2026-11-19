# index.html に「家族でつながるセーブ」と iPad アプリ用のタグを足す。
# 使いかた: python3 add_cloud_save.py <入力index.html> <出力index.html>
# もう足してある所はとばすので、何回やっても大丈夫。
import sys

src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf8').read()

def rep(old, new, what):
    global s
    if new in s:
        return
    if s.count(old) != 1:
        sys.exit(f'見つからない/2つ以上ある: {what} ({s.count(old)})')
    s = s.replace(old, new, 1)

# 1) <head> の先頭：文字コード・画面・iPad アプリ・Firebase の部品
HEAD = '''<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<meta name="tougei-build" content="dev">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black">
<meta name="apple-mobile-web-app-title" content="陶芸でGO">
<meta name="theme-color" content="#172126">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icon-180.png">
<link rel="icon" type="image/png" href="icon-192.png">
<script src="lib/firebase-app-compat.js"></script>
<script src="lib/firebase-database-compat.js"></script>
<script src="firebase-config.js?v=dev"></script>
<script src="fb-shim.js?v=dev"></script>
'''
if '<meta name="tougei-build"' not in s:
    assert s.lstrip().startswith('<title>'), 'index.html の先頭が <title> ではない'
    s = HEAD + s.lstrip()

# 2) three.js：同じフォルダの lib を先に使い、なければ cdnjs
rep('<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>',
    '<script src="lib/three-r128.min.js"></script>\n<script>window.THREE||document.write(\'<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"><\\/script>\')</script>',
    'three.js')

# 3) セーブ：sid と savedAt をつけ、家族のセーブ(TG)にも送る
rep('''// ───────────────── セーブ（この端末のブラウザに3人分） ─────────────────
const SAVE_KEY = 'tougei-go-v1';
let saves = [null,null,null];
try { const j = JSON.parse(localStorage.getItem(SAVE_KEY) || 'null'); if (Array.isArray(j) && j.length===3) saves = j; } catch(e) {}
let slot = -1, S = null;
function save(){
  if (slot<0 || !S) return;
  saves[slot] = S;
  try { localStorage.setItem(SAVE_KEY, JSON.stringify(saves)); }
  catch(e){ toast('セーブできなかったよ。店の器を売ると直るかも。'); }
}''',
'''// ───────────────── セーブ（この iPad の中＋家族のセーブ＝クラウド） ─────────────────
// 1人分のセーブには sid（ずっと同じ番号）と savedAt（セーブした時こく）がつく。
// クラウドにあって、この iPad にまだ中身がないセーブは「stub」（名前などだけ）。遊ぶときに読みこむ。
const SAVE_KEY = 'tougei-go-v1', MAX_SAVES = 6;
const TGc = () => (window.TG && window.TG.on) ? window.TG : null;
let saves = [null,null,null];
try { const j = JSON.parse(localStorage.getItem(SAVE_KEY) || 'null'); if (Array.isArray(j) && j.length>=3) saves = j.slice(0, MAX_SAVES); } catch(e) {}
let slot = -1, S = null;
function writeSaves(){
  try { localStorage.setItem(SAVE_KEY, JSON.stringify(saves)); return true; }
  catch(e){
    // いっぱいのとき：クラウドに送ってあるほかの人のセーブを「stub」にして場所をあける
    const tg = TGc(); let freed = false;
    if (tg) saves.forEach((s,i) => { if (s && !s.stub && i !== slot && tg.synced(s.sid, s.savedAt)){ saves[i] = stubOf(s.sid, s); freed = true; } });
    if (freed){ try { localStorage.setItem(SAVE_KEY, JSON.stringify(saves)); return true; } catch(e2){} }
    return false;
  }
}
function stubOf(sid, m){ return { stub:true, sid, name:m.name||'', day:m.day||1, money:m.money||0, rep:m.rep||0, hero:m.hero||'m', savedAt:m.savedAt||0 }; }
// 中身が変わったときだけ savedAt を新しくする（見ただけで「新しいセーブ」にならないように）
const lastJ = {};
function fp(s){ const a = s.savedAt; s.savedAt = 0; const j = JSON.stringify(s); s.savedAt = a; return j; }
function markClean(s){ if (s && !s.stub && s.sid) lastJ[s.sid] = fp(s); }
function touch(s){ if (!s || s.stub) return; if (!s.sid) s.sid = 'p' + Date.now().toString(36) + Math.random().toString(36).slice(2,6);
  const j = fp(s); if (lastJ[s.sid] === j && s.savedAt) return; lastJ[s.sid] = j; s.savedAt = Date.now(); const tg = TGc(); if (tg) tg.queue(s); }
function save(){
  if (slot<0 || !S) return;
  saves[slot] = S; touch(S);
  if (!writeSaves()) toast('セーブできなかったよ。店の器を売ると直るかも。');
}
// 最初の画面で、クラウドの一覧とこの iPad のセーブをあわせる（新しいほうを使う）
let syncing = false;
async function cloudSync(){
  const tg = TGc(); if (!tg || syncing) return; syncing = true;
  try {
    const fid = await tg.ready(); if (!fid) return;
    const metas = await tg.list(); if (!metas || screen !== 'title' || slot >= 0) return;
    let changed = false; const at = {};
    saves.forEach((s,i) => { if (!s) return; if (!s.sid){ touch(s); changed = true; } at[s.sid] = i; });
    for (const [sid, m] of Object.entries(metas)){
      const i = at[sid];
      if (i === undefined){
        if (m.del) continue;
        let k = saves.indexOf(null); if (k < 0){ if (saves.length >= MAX_SAVES) continue; k = saves.length; saves.push(null); }
        saves[k] = stubOf(sid, m); at[sid] = k; changed = true; continue;
      }
      const s = saves[i];
      if (m.del){ if ((m.savedAt||0) >= (s.savedAt||0)){ saves[i] = null; changed = true; } continue; }
      if ((m.savedAt||0) > (s.savedAt||0) + 1000){ saves[i] = stubOf(sid, m); changed = true; }
      else if (s.stub && (s.name !== m.name || s.day !== m.day || s.money !== m.money)){ saves[i] = stubOf(sid, m); changed = true; }
    }
    // この iPad のほうが新しいセーブは、クラウドへ送る
    saves.forEach(s => { if (!s || s.stub) return; const m = metas[s.sid]; if (!m || (!m.del && (m.savedAt||0) < (s.savedAt||0))) tg.queue(s); });
    tg.flush();
    if (changed){ writeSaves(); if (screen === 'title' && slot < 0) go('title', 'nosync'); }
  } finally { syncing = false; }
}''', 'save')

# 4) 最初の画面：stub の読みこみ・名前を変える/消すのクラウド対応・家族のセーブらん
rep('''SCREENS.title = () => {
  const slotHtml = saves.map((s,i)=> s''',
'''SCREENS.title = (arg) => {
  const list = saves.slice(); if (!list.includes(null) && list.length < MAX_SAVES) list.push(null);
  const slotHtml = list.map((s,i)=> s''', 'title slots')
rep('''<span class="muted">ここで新しく始める</span></button>`).join('');''',
    '''<span class="muted">ここで新しく始める</span></button>`).join('');
  const tg = TGc();''', 'title tg')
rep('''<p class="muted" style="font-size:13px">この iPad に 3人までセーブできるよ。</p>''',
    '''${tg ? '' : '<p class="muted" style="font-size:13px">この iPad に 3人までセーブできるよ。</p>'}
    <div id="cloudSec" style="${tg ? '' : 'display:none'}"></div>''', 'title note')
rep('''view().querySelectorAll('[data-ren]').forEach(b => b.onclick = () => { renSlot = +b.dataset.ren;''',
    '''if (tg){ tg.renderSec(); if (arg !== 'nosync') cloudSync(); }
  const openStub = async i => { const s = saves[i]; if (!s || !s.stub) return true; if (!tg){ toast('この iPad にはセーブの中身がないよ'); return false; }
    toast('家族のセーブを読みこんでいるよ…'); const full = await tg.get(s.sid);
    if (!full){ toast('読みこめなかったよ。インターネットにつながっているか見てね'); return false; }
    saves[i] = full; writeSaves(); return true; };
  view().querySelectorAll('[data-ren]').forEach(b => b.onclick = async () => { if (!(await openStub(+b.dataset.ren))) return; renSlot = +b.dataset.ren;''', 'title ren')
rep('''view().querySelectorAll('[data-play]').forEach(b => b.onclick = () => { slot = +b.dataset.play; S = saves[slot]; go('hub'); });''',
    '''view().querySelectorAll('[data-play]').forEach(b => b.onclick = async () => { const i = +b.dataset.play; if (b.disabled) return; b.disabled = true; const ok = await openStub(i); b.disabled = false; if (!ok || screen !== 'title') return; slot = i; S = saves[slot]; markClean(S); go('hub'); });''', 'title play')
rep('''if (b.dataset.armed){ saves[+b.dataset.del] = null; try{ localStorage.setItem(SAVE_KEY, JSON.stringify(saves)); }catch(e){} go('title'); }''',
    '''if (b.dataset.armed){ const old = saves[+b.dataset.del]; saves[+b.dataset.del] = null; writeSaves(); if (tg && old && old.sid) tg.remove(old.sid); go('title', 'nosync'); }''', 'title del')
rep('''saves[renSlot].name = nn; saves[renSlot].hero = sex; try{ localStorage.setItem(SAVE_KEY, JSON.stringify(saves)); }catch(e){} toast''',
    '''saves[renSlot].name = nn; saves[renSlot].hero = sex; touch(saves[renSlot]); writeSaves(); toast''', 'title rename')
rep('''<div class="slots">${slotHtml}</div>''',
    '''<div class="slots"${list.length > 3 ? ' style="gap:10px"' : ''}>${slotHtml}</div>''', 'slots gap')

# 5) 起動：アプリにもどってきたら最初の画面であわせる／とじる前にセーブ
rep('''go('title'); loadPeople();''',
    '''go('title'); loadPeople();
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') save(); else if (screen === 'title' && slot < 0) cloudSync(); });
window.addEventListener('pagehide', () => save());
window.addEventListener('tougei-save-now', () => save());''', 'boot')

open(dst, 'w', encoding='utf8').write(s)
print('ok', len(s))
