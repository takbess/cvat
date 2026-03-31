# CVATでscoreを表示する手順（確実版）

このドキュメントは、Auto Annotation 実行後に CVAT UI で `score` が見えない、または常に `1.0` になる場合の対処をまとめたものです。

## 結論（何を直せばよいか）

`score` 表示には、次の3点が必要です。

1. **Nuclio 関数が confidence を返す**
2. **backend が confidence/score を DB の score に保存する**
3. **UI が score を表示する**

どれか1つでも欠けると表示されません。

## 1) Nuclio 側: confidence を返す

MMDetection 関数の `main.py` で、推論結果に `confidence` を入れます。

- 対象:
  - `serverless/pytorch/openmmlab/mmdetection/yolox_s/nuclio/main.py`
  - `serverless/pytorch/openmmlab/mmdetection/rtmdet_s/nuclio/main.py`

期待する出力例:

```json
{
  "confidence": "0.9471",
  "label": "person",
  "type": "rectangle",
  "points": [ ... ]
}
```

## 2) backend 側: score への保存を保証する

`cvat/apps/lambda_manager/views.py` の `DetectionResultConverter._parse_score()` を次の仕様にします。

- `confidence` を優先して読む
- `confidence` がなければ `score` も読む
- どちらも無効な場合のみ `1.0` にフォールバック

これで、関数が `confidence` を返していても `score=1.0` 固定になる問題を防げます。

## 3) UI 側: source に依存せず score を表示する

### 右サイドバー

- `cvat-ui/src/components/annotation-page/standard-workspace/objects-side-bar/object-item-details.tsx`
- `withScore` を `Number.isFinite(score)` ベースにする

### キャンバスラベル

- `cvat-canvas/src/typescript/canvasView.ts`
- `withScore` を `!isSkeletonElement && Number.isFinite(score)` ベースにする

`source` 判定に依存すると、データに score があっても表示されないケースが出ます。

## 4) 反映（重要）

環境によってはコード修正後にコンテナへ自動反映されません。  
その場合は backend ファイルをコンテナへコピーして再起動します。

```bash
docker cp "cvat/apps/lambda_manager/views.py" \
  cvat_server:/home/django/cvat/apps/lambda_manager/views.py

docker cp "cvat/apps/lambda_manager/views.py" \
  cvat_worker_annotation:/home/django/cvat/apps/lambda_manager/views.py

docker restart cvat_server cvat_worker_annotation
```

UI 側は `cvat_ui` を再作成して反映します（ローカルビルド済み前提）。

```bash
docker compose -f docker-compose.yml -f components/serverless/docker-compose.serverless.yml \
  up -d --force-recreate cvat_ui
```

## 5) 確認手順

1. ブラウザをハードリロード（`Ctrl+Shift+R`）
2. **新規で** Automatic annotation を実行
3. 次を確認:
   - 右サイドバーに score が表示される
   - キャンバスラベルに `Confidence: 0.xx` が表示される

注意: 既存の古いアノテーションは `score=1.0` で保存済みの可能性があります。  
修正後に実行した新規結果で確認してください。

## 6) それでも `1.0` のままなら

- Nuclio 関数ログで `confidence` を返しているか確認
- `cvat_worker_annotation` ログで推論結果受け取り時のエラー確認
- 必要なら関数を再デプロイ

```bash
nuctl get functions --platform local
docker logs cvat_worker_annotation --tail 100
docker logs nuclio-nuclio-pth-openmmlab-mmdetection-yolox-s --tail 100
docker logs nuclio-nuclio-pth-openmmlab-mmdetection-rtmdet-s --tail 100
```
