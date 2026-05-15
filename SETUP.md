# CVAT + GPU 半自動アノテーション（YOLO）セットアップ手順

このドキュメントは、**CVAT を Docker Compose で起動し、Nuclio 経由で YOLO 系検出モデルを GPU で使う**までの手順をまとめたものです。公式ドキュメントの要点と、よくある誤りも併記します。

## 前提

- Docker / Docker Compose が使えること
- GPU を使う場合: [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) が有効であること（`nvidia-smi` がホストで動く）

## 1. CVAT と Nuclio（ダッシュボード）を同じ Compose で起動する

リポジトリのルートで次を実行します。**自動アノテーション用の Nuclio は `components/serverless/docker-compose.serverless.yml` で定義されています。**

```bash
# 基本はこちら
docker compose -f docker-compose.yml -f components/serverless/docker-compose.serverless.yml up -d
# WSL2の時、再起動時にポート番号が変わったりするため以下
docker compose -f docker-compose.yml \
  -f components/serverless/docker-compose.serverless.yml \
  -f docker-compose.lambda-wsl2.yml up -d
```

`docker-compose.lambda-wsl2.yml` は WSL2 上で Nuclio 関数へ確実に届けるためのパッチ（`views.py` マウント）です。

開発用オーバーレイを併用する場合（任意）:

```bash
# 基本はこちら
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f components/serverless/docker-compose.serverless.yml up -d
# WSL2の時
docker compose -f docker-compose.yml -f docker-compose.dev.yml \
  -f components/serverless/docker-compose.serverless.yml \
  -f docker-compose.lambda-wsl2.yml up -d
```

### 重要: 手動で Nuclio ダッシュボードを別起動しない

次のように **ホストの 8070 を占有する** `nuclio-dashboard` を別途 `docker run` すると、上記 compose の `nuclio` サービス（同じく 8070）と **ポート競合** し、CVAT 側から Nuclio に繋がらない原因になります。

```text
# 避ける: 公式 compose と二重になる
docker run -d --name nuclio-dashboard -p 8070:8070 -v /var/run/docker.sock:/var/run/docker.sock quay.io/nuclio/dashboard:...
```

Nuclio の UI は compose が立てた `nuclio` コンテナ経由で `http://localhost:8070` にアクセスします。

## 2. `nuctl` のインストール

関数のビルド・デプロイに `nuctl` が必要です。**Nuclio ダッシュボードのイメージタグ**（`components/serverless/docker-compose.serverless.yml` 内の `quay.io/nuclio/dashboard:...`）に合わせたバージョンを [Nuclio Releases](https://github.com/nuclio/nuclio/releases) から取得してください。

例（バージョンはファイルのタグに合わせて置き換える）:

```bash
wget "https://github.com/nuclio/nuclio/releases/download/<VERSION>/nuctl-<VERSION>-linux-amd64"
chmod +x nuctl-<VERSION>-linux-amd64
sudo mv nuctl-<VERSION>-linux-amd64 /usr/local/bin/nuctl
nuctl version
```

## 3. YOLO（GPU）のデプロイ

このリポジトリの `develop` では、**OpenVINO の `yolo-v3-tf` 用 serverless ディレクトリは同梱されていません。**
半自動アノテーションで YOLO 系を使う場合は、同梱されている **YOLOv7（ONNX）** をデプロイします。

```bash
./serverless/deploy_gpu.sh serverless/onnx/WongKinYiu/yolov7/nuclio
```

CPU のみの場合:

```bash
./serverless/deploy_cpu.sh serverless/onnx/WongKinYiu/yolov7/nuclio
```

### デプロイ確認

```bash
nuctl get function --platform local
```

`onnx-wongkinyiu-yolov7` が `ready` であれば成功です。

## 4. CVAT 画面での利用

1. ブラウザで CVAT にログイン（通常は `http://localhost:8080`）。
2. 対象タスクを開く。
3. **Actions → Automatic annotation**（または同等の自動アノテーション操作）から **YOLO v7** / `onnx-wongkinyiu-yolov7` を選択。

一覧に出ない場合は、ブラウザの強制再読み込みや、一度ログアウト／ログインを試してください。

## 5. よくある失敗と対処

| 症状 | 原因の例 | 対処 |
|------|-----------|------|
| `stat .../function.yaml: no such file` | 存在しないパス（例: `serverless/openvino/omz/public/yolo-v3-tf`）を指定した | 上記の **YOLOv7** パスを使う |
| `Bind for 0.0.0.0:8070 failed: port is already allocated` | 手動 `nuclio-dashboard` などが 8070 を使用中 | 競合コンテナを停止・削除し、serverless 用 compose のみで起動 |
| 関数は `ready` だが CVAT にモデルが出ない | `cvat_server` が `nuclio` に到達できていない | serverless compose で `nuclio` と `cvat_server` が同じネットワークで起動しているか確認。手動ダッシュボードをやめる |
| **Fetching inference status for task #N** / 自動アノテーション直後に失敗 | WSL2 で `host.docker.internal` + 誤った Nuclio ポート、または関数 URL の不整合 | 下記「自動アノテーション接続エラー」を参照 |
| GPU が使われない | `deploy_gpu.sh` の関数に GPU リソースが付いていない、またはドライバ/Toolkit 不備 | `nvidia-smi`、Nuclio 関数コンテナのログを確認 |

### 自動アノテーション接続エラー（WSL2 / Docker Desktop）

`docker-compose.lambda-wsl2.yml` でパッチ済み `views.py` をマウントし、Docker ネットワーク上の `nuclio-nuclio-<関数名>:8080` へ直接呼び出すようにしています（WSL2 で `host.docker.internal` が使えない問題の対策）。

**compose を更新したあと**は CVAT を再起動してください。

```bash
docker compose -f docker-compose.yml \
  -f components/serverless/docker-compose.serverless.yml \
  -f docker-compose.lambda-wsl2.yml up -d
```

ログ確認:

```bash
docker logs cvat_worker_annotation --tail 80
```

`host.docker.internal` への `ConnectionError` が出なくなれば解消です。

## 6. 停止

```bash
# 基本はこちら
docker compose -f docker-compose.yml -f components/serverless/docker-compose.serverless.yml down

# WSL2の時
docker compose -f docker-compose.yml \
  -f components/serverless/docker-compose.serverless.yml \
  -f docker-compose.lambda-wsl2.yml down
```

開発用オーバーレイを付けた場合は、同じ `-f` の組み合わせで `down` してください。

## 7. 再起動
```bash
# 基本はこちら
docker compose -f docker-compose.yml -f components/serverless/docker-compose.serverless.yml up -d
# WSL2の時
docker compose -f docker-compose.yml \
  -f components/serverless/docker-compose.serverless.yml \
  -f docker-compose.lambda-wsl2.yml up -d
```
---

参考（公式）: [Semi-automatic and Automatic Annotation (installation)](https://github.com/cvat-ai/cvat/blob/develop/site/content/en/docs/administration/community/advanced/installation_automatic_annotation.md)


# アカウント
tak bes
pff...@gmail.com
takbes
PhysDoctor001
