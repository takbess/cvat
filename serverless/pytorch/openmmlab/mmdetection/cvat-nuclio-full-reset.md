# CVAT/Nuclio 完全リセット手順（データ込み）

このドキュメントは、**CVAT/Nuclio 関連だけ**を対象に、  
**コンテナ・イメージ・ボリューム（データ）を全削除**し、**ゼロから再構築**する手順をまとめたものです。

## 対象と注意点

- 対象: CVAT 本体、CVAT worker 群、Nuclio、Nuclio 関数、CVAT 関連 volume/network
- 非対象: 他プロジェクトの Docker コンテナ/イメージ/ボリューム
- 注意: `-v` を使うため、CVAT のタスク/プロジェクト/アノテーション等の永続データは削除されます

## 1) CVAT/Nuclio 関連を停止・削除（データ込み）

CVAT リポジトリのルートで実行:

```bash
docker compose \
  -f docker-compose.yml \
  -f components/serverless/docker-compose.serverless.yml \
  down -v --rmi all --remove-orphans
```

## 2) 残骸（Nuclio 関数コンテナ・関連イメージ）を追加削除

`down` 後でも Nuclio 管理の関数コンテナが残る場合があるため、明示的に削除します。

```bash
docker rm -f \
  nuclio-nuclio-pth-openmmlab-mmdetection-rtmdet-s \
  nuclio-nuclio-pth-openmmlab-mmdetection-yolox-s \
  nuclio-nuclio-onnx-wongkinyiu-yolov7 \
  nuclio-local-storage-reader || true
```

必要に応じて関連イメージも削除:

```bash
docker rmi \
  cvat.pth.openmmlab.mmdetection.rtmdet_s:latest-gpu \
  cvat.pth.openmmlab.mmdetection.yolox_s:latest-gpu \
  cvat.onnx.wongkinyiu.yolov7:latest-gpu \
  cvat.openvino.base:latest || true
```

## 3) CVAT + serverless を再構築・起動

```bash
docker compose \
  -f docker-compose.yml \
  -f components/serverless/docker-compose.serverless.yml \
  up -d --build
```

初回はイメージ取得で時間がかかります。

## 4) Nuclio 関数を再デプロイ

再構築直後は関数が `unhealthy` のことがあるため、使うモデルを再デプロイします。

```bash
DOCKER_BUILDKIT=0 ./serverless/deploy_gpu.sh serverless/pytorch/openmmlab/mmdetection/yolox_s/nuclio
DOCKER_BUILDKIT=0 ./serverless/deploy_gpu.sh serverless/pytorch/openmmlab/mmdetection/rtmdet_s/nuclio
DOCKER_BUILDKIT=0 ./serverless/deploy_gpu.sh serverless/onnx/WongKinYiu/yolov7/nuclio
```

## 5) 状態確認

コンテナ状態:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

Nuclio 関数状態:

```bash
nuctl get functions --platform local
```

期待値:

- `cvat_server`, `cvat_ui`, `cvat_worker_annotation` などが `Up`
- Nuclio 関数 (`yolox-s`, `rtmdet-s`, `yolov7`) が `ready`

## 6) 利用開始

- CVAT: <http://localhost:8080>
- タスク画面で **Automatic annotation** を開き、対象モデルを選んで実行

## トラブル時の最小チェック

- `Automatic annotation failed` の場合:
  - `docker logs cvat_worker_annotation --tail 100`
  - `docker logs nuclio-nuclio-pth-openmmlab-mmdetection-yolox-s --tail 100`
  - `docker logs nuclio-nuclio-pth-openmmlab-mmdetection-rtmdet-s --tail 100`
  - `docker logs nuclio-nuclio-onnx-wongkinyiu-yolov7 --tail 100`
- 関数が `unhealthy` の場合:
  - 該当関数のみ `deploy_gpu.sh` で再デプロイ
