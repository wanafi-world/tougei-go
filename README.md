# 陶芸でGO（GitHub Pages 版）

iPad で遊べる陶芸ゲームです。

- 遊ぶ：GitHub Pages の URL を Safari で開き、「共有」→「ホーム画面に追加」。ホーム画面から開くと全画面になります。
- セーブ：はじめに「家族のあいことば」を入れると、Firebase Realtime Database にセーブが送られ、同じあいことばの iPad どうしで同じセーブが見えます（ログインなし。家族ID = SHA-256("tougei-family:" + あいことば)）。
  - 一覧 `fam/<家族ID>/m/<sid>`、中身 `fam/<家族ID>/s/<sid>`（JSON 文字列）。15秒まとめ送り＋アプリをとじる瞬間にすぐ送る。新しいほうのセーブを使う。
- 設定：`firebase-config.js` に databaseURL を入れる。ルールは `database.rules.json`。
- 更新：ゲームを直したら `python3 tools/bump.py` → commit → push。iPad に「新しいゲームがあるよ」が出ます。
- 元の index.html（プロジェクトの tougei-go/index.html）にセーブのしくみを足すのは `python3 tools/add_cloud_save.py 入力 出力`（何回やっても同じ結果）。
