# index.html に「管理画面」を足す（add_cloud_save.py のあとに使う）。
# 開きかた：最初の画面の「陶芸でGO」の文字を 2びょう おしたままにする。
# 使いかた: python3 add_admin.py <入力index.html> <出力index.html>（何回やっても同じ）
import sys

src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf8').read()
if 'function openAdmin' in s:
    open(dst, 'w', encoding='utf8').write(s); print('already'); sys.exit()
assert 'function cloudSync' in s, '先に add_cloud_save.py を使ってね'

ADMIN = r'''
// ───────────────── 管理画面（最初の画面の「陶芸でGO」を2びょうおす） ─────────────────
let admT = -1, admWipe = 0;
const admKB = o => { try { return Math.round(JSON.stringify(o).length/1024); } catch(e){ return 0; } };
function bindAdmin(){
  const h = view().querySelector('.title-card h1'); if (!h) return;
  let t = null; const stop = () => { clearTimeout(t); t = null; };
  h.style.touchAction = 'none';
  h.addEventListener('pointerdown', () => { stop(); t = setTimeout(() => { t = null; sfx('chime', 0.6); openAdmin(); }, 2000); });
  ['pointerup','pointerleave','pointercancel'].forEach(e => h.addEventListener(e, stop));
  h.addEventListener('contextmenu', e => e.preventDefault());
}
function openAdmin(){
  let ov = document.getElementById('admOv');
  if (!ov){
    ov = document.createElement('div'); ov.id = 'admOv';
    ov.style.cssText = 'position:fixed;inset:0;z-index:180;display:flex;align-items:center;justify-content:center;padding:16px;background:rgba(10,14,17,.75)';
    ov.innerHTML = '<div class="panel" style="width:min(760px,100%);max-height:100%;overflow:auto;-webkit-overflow-scrolling:touch;touch-action:pan-y;background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:16px 18px"><div class="row" style="justify-content:space-between;align-items:center"><h2 style="margin:0;font-family:var(--display)">管理画面</h2><button id="admClose" class="primary">とじる</button></div><div id="admBody"></div></div>';
    document.body.appendChild(ov);
    ov.querySelector('#admClose').onclick = closeAdmin;
  }
  ov.hidden = false; admWipe = 0; renderAdmin();
}
function closeAdmin(){ const ov = document.getElementById('admOv'); if (ov) ov.hidden = true; admT = -1; if (screen === 'title' && slot < 0) go('title', 'nosync'); }
function admSec(body, title){ const d = document.createElement('div'); d.style.cssText = 'border-top:1px dashed var(--line);padding:10px 0'; d.innerHTML = `<h3 style="margin:0 0 6px;font-size:16px">${title}</h3>`; body.appendChild(d); return d; }
function admBtn(sec, label, fn, primary){ const b = document.createElement('button'); b.textContent = label; if (primary) b.className = 'primary'; b.style.cssText = 'margin:3px;padding:6px 12px;min-height:40px;font-size:15px'; b.onclick = () => fn(b); sec.appendChild(b); return b; }
function admDone(){ const T = saves[admT]; if (T){ touch(T); if (!writeSaves()) toast('セーブできなかったよ（いっぱい）'); } sfx('tap', 0.5); renderAdmin(); }
async function renderAdmin(){
  const body = document.getElementById('admBody'); if (!body) return; body.innerHTML = '';
  const tg = TGc();
  // だれのセーブ
  let sec = admSec(body, 'セーブ');
  const st = tg ? tg.status() : null;
  sec.insertAdjacentHTML('beforeend', `<p class="muted" style="font-size:13px;margin:0 0 6px">${tg ? (st && st.s === 'skip' ? '家族のあいことばがまだだよ。この iPad の中だけ。' : '家族のセーブ（クラウド）とつながっているよ。ここで変えると、ほかの iPad にもうつるよ。') : 'この iPad の中だけのセーブだよ。'}</p>`);
  saves.forEach((s, i) => {
    if (!s) return;
    const row = document.createElement('div'); row.className = 'row'; row.style.cssText = 'align-items:center;gap:6px;flex-wrap:wrap;padding:4px 0' + (i === admT ? ';background:var(--ai-soft);border-radius:10px;padding:4px 8px' : '');
    row.innerHTML = `<strong style="min-width:7em">${esc(s.name)}</strong><span class="muted num" style="font-size:13px">${s.day}日目・${yen(s.money)}・${s.stub ? 'クラウドだけ' : admKB(s) + 'KB'}${s.savedAt ? '・' + new Date(s.savedAt).toLocaleString('ja-JP', {month:'numeric', day:'numeric', hour:'numeric', minute:'2-digit'}) : ''}</span><span style="flex:1"></span>`;
    admBtn(row, i === admT ? 'えらんでいる' : 'えらぶ', async () => {
      if (s.stub){ if (!tg) return; toast('読みこんでいるよ…'); const full = await tg.get(s.sid); if (!full){ toast('読みこめなかったよ'); return; } saves[i] = full; writeSaves(); }
      admT = i; renderAdmin();
    }, i === admT);
    admBtn(row, '消す', b => {
      if (!b.dataset.armed){ b.dataset.armed = '1'; b.textContent = 'もう一度おすと消えるよ'; return; }
      const old = saves[i]; saves[i] = null; writeSaves(); if (tg && old && old.sid) tg.remove(old.sid); if (admT === i) admT = -1; renderAdmin();
    });
    sec.appendChild(row);
  });
  if (!saves.some(Boolean)) sec.insertAdjacentHTML('beforeend', '<p class="muted">セーブがないよ。</p>');

  const T = saves[admT];
  if (T && !T.stub){
    const R = (() => { let k = 0; RANKS.forEach((r, j) => { if (T.rep >= r.min) k = j; }); return k; })();
    sec = admSec(body, `お金（いま ${yen(T.money)}）`);
    [[1000,'+1,000'],[10000,'+10,000'],[100000,'+100,000']].forEach(([v,l]) => admBtn(sec, l, () => { T.money += v; admDone(); }));
    admBtn(sec, '0にする', () => { T.money = 0; admDone(); });
    sec = admSec(body, `ひょうばん（いま ${T.rep}・${RANKS[R].name}）`);
    [10, 50].forEach(v => admBtn(sec, '+' + v, () => { T.rep += v; admDone(); }));
    admBtn(sec, '-10', () => { T.rep = Math.max(0, T.rep - 10); admDone(); });
    RANKS.forEach((r, j) => admBtn(sec, 'レベル' + (j+1), () => { T.rep = r.min; admDone(); }, j === R));
    sec = admSec(body, `日（いま ${T.day}日目）`);
    admBtn(sec, '+1日', () => { T.day += 1; admDone(); });
    admBtn(sec, '+10日', () => { T.day += 10; admDone(); });
    admBtn(sec, '1日目にもどす', () => { T.day = 1; admDone(); });
    sec = admSec(body, '土（ぜんぶの土を）');
    admBtn(sec, '+5こずつ', () => { Object.keys(CLAYS).forEach(c => T.clay[c] = (T.clay[c]||0) + 5); admDone(); });
    admBtn(sec, '0こにする', () => { Object.keys(CLAYS).forEach(c => T.clay[c] = 0); admDone(); });
    sec.insertAdjacentHTML('beforeend', `<p class="muted" style="font-size:13px;margin:4px 0 0">${Object.keys(CLAYS).map(c => CLAYS[c].name + ' ' + (T.clay[c]||0)).join('・')}</p>`);
    sec = admSec(body, `かま（いま ${KILNS[T.kiln] ? KILNS[T.kiln].name : T.kiln}）`);
    admBtn(sec, 'ぜんぶのかまをもらう', () => { T.owned = Object.keys(KILNS); admDone(); });
    Object.keys(KILNS).forEach(k => admBtn(sec, KILNS[k].name + 'を使う', () => { if (!T.owned.includes(k)) T.owned.push(k); T.kiln = k; admDone(); }, T.kiln === k));
    sec = admSec(body, 'こうぼう');
    admBtn(sec, T.apprentice ? '弟子：いる → いなくする' : '弟子：いない → よぶ', () => { T.apprentice = !T.apprentice; admDone(); });
    admBtn(sec, T.expanded ? '店：広い → もとにもどす' : '店：ふつう → 広げる', () => { T.expanded = !T.expanded; admDone(); });
    admBtn(sec, '注文を入れかえる', () => { const keep = S; S = T; S.orders = []; refillOrders(); S = keep; admDone(); });
    sec = admSec(body, `器（店 ${T.stock.length}こ・かんそうだな ${T.queue.length}こ）`);
    admBtn(sec, '店の器をぜんぶ消す', b => { if (!b.dataset.armed){ b.dataset.armed = '1'; b.textContent = 'もう一度おすと消えるよ'; return; } T.stock = []; admDone(); });
    admBtn(sec, 'かんそうだなを空にする', b => { if (!b.dataset.armed){ b.dataset.armed = '1'; b.textContent = 'もう一度おすと消えるよ'; return; } T.queue = []; admDone(); });
  } else if (saves.some(Boolean)) {
    body.insertAdjacentHTML('beforeend', '<p class="muted" style="padding:6px 0">上で「えらぶ」をおすと、お金・ひょうばん・日・土・かまなどを変えられるよ。</p>');
  }

  sec = admSec(body, 'この iPad');
  if (tg) admBtn(sec, 'クラウドとあわせる', async () => { await tg.flush(); admT = -1; closeAdmin(); go('title'); toast('家族のセーブとあわせたよ'); });
  admBtn(sec, 'この iPad のセーブをぜんぶ消す', b => {
    if (admWipe < 1){ admWipe = 1; b.textContent = 'もう一度おすと消えるよ（クラウドは消えない）'; return; }
    try { Object.keys(localStorage).filter(k => k.startsWith('tougei')).forEach(k => localStorage.removeItem(k)); } catch(e){}
    location.reload();
  });
}
'''

def rep(old, new, what):
    global s
    if s.count(old) != 1:
        sys.exit(f'見つからない/2つ以上ある: {what} ({s.count(old)})')
    s = s.replace(old, new, 1)

rep("// ───────────────── 起動 ─────────────────", ADMIN + "\n// ───────────────── 起動 ─────────────────", 'boot mark')
rep("if (tg){ tg.renderSec(); if (arg !== 'nosync') cloudSync(); }",
    "if (tg){ tg.renderSec(); if (arg !== 'nosync') cloudSync(); }\n  bindAdmin();", 'title bind')
open(dst, 'w', encoding='utf8').write(s)
print('ok', len(s))
