
## PC再起動後の復旧手順（重要）

PC再起動後は、Nuclio関数の公開ポート（NODE PORT）が変わることがあります。
このとき CVAT が古いポートへ接続しようとして、`Automatic annotation failed` になる場合があります。

### 1) まず状態確認

```bash
docker ps --format '{{.Names}}\t{{.Status}}'
nuctl get function --platform local
```

- `cvat_server`, `cvat_worker_annotation`, `nuclio` が `Up`
- `pth-openmmlab-mmdetection-rtmdet-s` が `ready`

を確認します。

### 2) 失敗時の最短復旧（推奨）

```bash
DOCKER_BUILDKIT=0 ./serverless/deploy_gpu.sh serverless/pytorch/openmmlab/mmdetection/rtmdet_s/nuclio
```

この再デプロイで、現在有効な NODE PORT に合わせて関数定義が更新されます。

### 3) それでも失敗する場合

`host.docker.internal` 経由の到達性を取り直すため、CVAT サーバ・注釈ワーカーを再作成します。

```bash
docker compose -f docker-compose.yml -f components/serverless/docker-compose.serverless.yml \
  up -d --force-recreate cvat_server cvat_worker_annotation
```

その後、もう一度 2) の再デプロイを実行します。

### 4) 接続テスト（必要な場合）

ワーカーから RTMDet 関数ポートへ接続できるか確認します（`<PORT>` は `nuctl get function` で確認）。

```bash
docker exec cvat_worker_annotation python - << 'PY'
import socket
port = <PORT>
try:
    s = socket.create_connection(("host.docker.internal", port), 3)
    print("connect ok", s.getpeername())
    s.close()
except Exception as e:
    print("connect fail", e)
PY
```

### 5) スコア表示まで確認する場合

- Auto labeling 実行時は `cleanup` を ON にして古い形状を消す
- 実行後に `Ctrl+Shift+R` でハードリロード
- それでも表示されない場合は `cvat_ui` を再作成

```bash
docker compose -f docker-compose.yml -f components/serverless/docker-compose.serverless.yml \
  up -d --force-recreate cvat_ui
```