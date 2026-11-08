# Cloud Spiral × CBDK — v0.3.1 UI 実験

GitHub Actionsを使用してBlender実機テストを行う**公開**実験用リポジトリ。コードおよびActions成果物は第三者に閲覧され得るため、個人データや非公開の3Dモデルを追加しない。

## ファイル
- `addon/cloud_spiral_lobe_builder_v031.py`：最新v0.3.1（旧v0.3を残して非破壊変更）
- `addon/cloud_spiral_lobe_builder_v03.py`：比較用のv0.3
- `scripts/native_smoke.py`：実Blenderでアドオン登録・生成・トポロジー・UI新機能・再登録を検査
- `scripts/cbdk_static.py`：公開CBDKのコミットを固定して解析するジョブ
- `.github/workflows/cloud-blender-ci.yml`：Blender 4.4.3 / 4.5.15 / 5.2.1 と CBDK静的解析

## v0.3.1の変更点
- **溝スタイル**：ふんわり／くっきり／標準をボタンで適用。半径・分割数を維持して溝の深さ、幅、縁の丸み、ドーム高さだけを変更。
- **3ローブの調整**：左右ローブの「広がり」「大きさ」を個別に変更。いずれも`1.0`で旧標準配置を再現。
- **詳細設定の折りたたみ**：通常は主要項目のみ。細かい螺旋・中央トポロジー・解像度は切り替え表示。
- **操作ヒント**：スタイルの適用後に生成ボタンを押す。オブジェクトモード以外では生成を無効化。
- **デフォルトの幾何形状はv0.3と同じ**。旧ソースは改変せず保持。

## インストール・操作
1. GitHub Actionsの成功した`cloud-static-and-addon-...` artifactを取得し、ZIP内の`Cloud_Spiral_Lobe_Builder_v0.3.1.zip`を展開・インストールする（またはPythonファイルを直接インストール）。
2. Blenderのプリファレンスからアドオンを有効化し、3Dビューの`N`キーで**Cloud Spiral**タブを表示。
3. 「単体」または「参考画像風3個」を選択し、必要なら溝スタイルと広がり・大きさを変更して「渦雲を生成」を押す。
4. 初期の`1.0`設定で従来と同じ3ローブ配置に戻る。

## 品質ゲート
- GitHub Actionsで各Blenderの実行ログに`CLOUD_REAL_BLENDER: PASS`を確認して初めてネイティブ成功とする。
- CBDKはBlender API静的解析用。CIでは参照コミット`8665a3c136ae81efbd28a820e7de50ef6ee59332`に固定。
- ヘッドレス検査はWindowsのクリック操作やUndo体験、造形美、自己交差なし、3Dプリント適性を保証しない。
- PRはすべての必要な検証が揃うまでドラフト・未マージ。

## 制限
生成は追加オブジェクト方式で既存形状をリアルタイムには変更しない。3ローブは独立したオブジェクト。単体モードで「交互」選択時は反時計扱い。

[Notionの実験管理](https://app.notion.com/p/412948b7493781d092b2eb7dc2f1e048)
