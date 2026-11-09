# Cloud Spiral × CBDK — v0.4 ふっくら雲ローブ実験

**最新版：Cloud Spiral Lobe Builder v0.4（Linux 3版＋Windows 4.4.3＋Linux画面付きGUIのCI合格。Windowsの人による最終受入は未実施）**

> このGitHubリポジトリは **Public**。個人データ・非公開の3D素材を追加しないこと。変更はドラフトPR #1に保持し、mainには統合していない。

## Windowsの操作・見た目の最終確認キット

**[ワンクリック確認キットZIP（2026-11-09の全6ジョブ成功版）](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42545843598/artifacts/13643057294)**

ZIPを展開して`run_windows_review.bat`を開くと、Blenderの**新しいテスト用シーン**に単体1個と3ローブ3個を自動準備します。`N`キーから`Cloud Spiral`で既存機能を操作し、`Cloud QA`で「合格・不具合・未確認」を項目別に記録できます。結果はローカルの`qa-output/cloud_review_*.json`に保存され、**送信は自動では行いません**。

- 4項目のWindows操作検証（CLD-04）と2項目の造形評価（CLD-06）を**独立して判定**。すべて明示的に合格するまで未完了。
- Windows実Blender 4.4.3のセットアップ・レポート書き出し・合否判定とLinux XvfbのCloud QAパネル起動スモークをCIで確認済み。ただし**人の実Windowsクリックと造形の評価は未確認**。
- 既存の`.blend`ファイルは上書きしません。使用方法と確認項目は[日本語README](WINDOWS_REVIEW_README.md)。
- バージョンや個人メモは結果JSONに含まれるため、**共有前に内容を確認**してください。

## ダウンロードと使用方法
- [GitHub Actions v0.4 成功実行](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42539777746)
- [v0.4 インストールZIPを含む成果物](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42539777746/artifacts/13641066019)
- [実Blender 4.4.3の新旧比較画像・検査JSON](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42539777746/artifacts/13640837847)
- [v0.4 GUI画面・Undo/Redo結果](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42539777746/artifacts/13640946735)

1. `Cloud_Spiral_Lobe_Builder_v0.4.zip` を入手し、Blenderのアドオンとしてインストール。有効化できない場合はZIP内の `cloud_spiral_lobe_builder_v04.py` を直接指定。
2. 3DビューのNキー → Cloud Spiralタブ → 「単体」または「参考画像風3個」。
3. 「雲の輪郭」は**ふっくら**（デフォルト）と**従来の彫刻**を選択可能。
4. 「ふくらみ」「外周のうねり」「底面の丸み」と、従来の「溝スタイル」を調整して「渦雲を生成」。

## v0.4の変更
- 厚みを増した上面ドーム、円周上の穏やかな凹凸、底面へ丸め込む6段の側面リング。
- 旧版の形状を完全再現できるCLASSICモードを追加。Blender検証で頂点・ポリゴン座標の一致を確認。
- Blender 4.4.3の初期設定・半径1の場合、最大高さ **0.300→0.850（2.83倍）**、体積 **0.697→1.732（2.48倍）**。境界辺・面向き矛盾・非多様体は0。
- 新たな`scripts/puffy_geometry_compare.py`で、**旧v0.3.1との比較・3パラメータが形状に与える効果**を検査。

## 主要ファイル
- `addon/cloud_spiral_lobe_builder_v04.py`：最新版。
- `addon/cloud_spiral_lobe_builder_v031.py`：前回のv0.3.1を保持（変更なし）。
- `scripts/native_smoke.py`：基本生成・トポロジー・3ローブ・UI設定のBlender検査。
- `scripts/blender_quality_gate.py`：不正値・編集中ガード・途中例外の後片付け。
- `scripts/puffy_geometry_compare.py`：旧版互換性と立体度を比較、PNG書き出し。
- `scripts/gui_smoke.py`：Linux Xvfb Blender実GUIのNパネル、生成、Ctrl+Z/Redoと画面PNG。
- `.github/workflows/cloud-blender-ci.yml`：Blender 4.4.3/4.5.15/5.2.1 + Linux GUI + CBDK解析。

## 検証の限界
- 5/5のCI成功は**技術的な動作確認**。Windowsでのマウス操作感、理想の雲造形、複数ローブの一体化、自己交差と3Dプリント適性の保証ではない。
- 現在のシルエットは「**厚みのある渦彫りの丸いローブ**」。リアルな積雲の塊が融合した見た目は次の改善対象。
- このレポジトリはPublic。Actions artifactsも閲覧・保持期限あり（約30日）。
- 実作業総時間およびCBDKの効率化時間は測定していないため、短縮率は主張しない。

[CLD-06 v0.4の詳細検証結果](docs/CLD06_V04_RESULTS.md) · [CLD-01〜05の引き継ぎ](docs/CLD04_CLD05_RESULTS.md) · [Notion進捗](https://app.notion.com/p/413948b749378104a06ac74679c8b9dd)

## 完了判定とCBDKへの振り返り
- **現在のロードマップが受入基準を満たして100%になったら、追加開発を止めて完了を案内する。** 次に「続けてー」と来ても、新しい版や工程を勝手に作らず「今回のロードマップは100%完了しているよー！」と伝える。
- 完了時は苦労・失敗・対処・次回の改善手順・CBDKへ転用する候補・実測証拠を最終レポートに追記する。
- [100%停止ルールとCBDK向けノウハウ](docs/COMPLETION_GATE_AND_CBDK_LESSONS.md) / [CBDK Notionの引き継ぎページ](https://app.notion.com/p/413948b7493781f68756d61534df149b)。
- 原MVPはCLD-01〜05の4/5=80%。CLD-04のWindows受入は未完了。CLD-06は別計画（90%）。数字の書き換えだけで100%にしない。
