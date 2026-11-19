# 版を上げる：index.html の tougei-build・自作スクリプトの ?v= ・version.json をそろえる
# 使いかた: python3 bump.py "変わったこと1" "変わったこと2" …
#   書いた文は、ゲームの中の「新しいゲームがあるよ」「ゲームが新しくなったよ」のお知らせに出る。
#   何も書かないと、前のお知らせのまま。文は小学4年生までの漢字で。
import re, time, json, os, sys
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(root, 'index.html'); s = open(p, encoding='utf8').read()
v = time.strftime('%Y%m%d-%H%M', time.gmtime())
s = re.sub(r'<meta name="tougei-build" content="[^"]*">', f'<meta name="tougei-build" content="{v}">', s, count=1)
s = re.sub(r'src="(firebase-config\.js|fb-shim\.js)(\?v=[^"]*)?"', lambda m: f'src="{m.group(1)}?v={v}"', s)
open(p, 'w', encoding='utf8').write(s)
vp = os.path.join(root, 'version.json'); notes = sys.argv[1:]
if not notes:
    try: notes = json.load(open(vp, encoding='utf8')).get('notes', [])
    except Exception: notes = []
json.dump({'v': v, 'notes': notes}, open(vp, 'w', encoding='utf8'), ensure_ascii=False)
print(v, len(notes))
