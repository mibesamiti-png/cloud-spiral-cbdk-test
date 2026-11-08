# Cloud Spiral × CBDK — private Blender CI experiment

**実験ID：CBDK-EXP-CLOUD-001**。旧雲アドオン v0.2 を再利用した v0.3 を、Private GitHub Actions 上の本物の Blender で確認する実験です。

このリポジトリは **Private** のまま運用してください。オリジナルの雲アドオンソース、生成 .blend、画像、Actions artifacts を公開リポジトリへコピーしないでください。

## ファイル
- `addon/cloud_spiral_lobe_builder_v03.py` — v0.3 試作コード（旧v0.2を非破壊で再利用）
- `scripts/native_smoke.py` — Blender実機の登録・単体/3ローブ生成・設定変更・幾何・再登録の検査
- `scripts/cbdk_static.py` — 公開CBDKのソースコードを読み取り専用cloneして静的スキャン
- `.github/workflows/cloud-blender-ci.yml` — Blender 4.4.3 / 4.5.15 / 5.2.1 + CBDK解析
- GitHub Actions の artifacts — ZIP、`.blend`、JSONレポート、Blenderログ、可能ならプレビューPNG

## 動作条件
Workflow は `test/cloud-v03-blender-native` ブランチへのpush、main向けPR、手動操作（GitHub UI）をトリガーとして設定。公開CBDK参照SHAは `8665a3c136ae81efbd28a820e7de50ef6ee59332` に固定。

**判定ルール：** 4件のジョブが実際に起動し、Blenderのネイティブログで `CLOUD_REAL_BLENDER: PASS` を確認して初めて「実Blender検証済」とする。ソースとCI設定をコミットしただけでは成功としない。

## 現在の注意事項：初回のGitHub Actionsが実行前に失敗
[初回実行 #42500401661](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42500401661) は、全4ジョブが数秒で `failure`。ジョブログのstepは空で、runner_nameも空だった。**テストが開始された証拠はなく、雲アドオンが失敗したことも意味しない。**

GitHub Actionsの該当実行ページの上部や各ジョブに、実行環境・Actions使用許可・請求設定に関するメッセージがないか確認してください。具体的な原因は現時点で未確認。制約を解消した後に再実行し、実ログとartifactsで判断します。

## これからの方針
- Blender CIの成功が確認できるまではCLD-02を「検証待ち」、CLD-04を「進行中」に据え置く。
- Windows対話GUI／Nパネルの配置・Undo感触・渦の美観・印刷適性は別途確認し、CI成功と混同しない。
- 主要な状態は[Notion実験ページ](https://app.notion.com/p/412948b7493781d092b2eb7dc2f1e048)で確認。
