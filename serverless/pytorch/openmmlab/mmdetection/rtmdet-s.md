# CVAT で MMDetection RTMDet-s を使う（サーバレス自動アノテーション）

このドキュメントは、CVAT の **Automatic annotation** 用に **OpenMMLab MMDetection の RTMDet-s（COCO 事前学習）** を Nuclio 関数として動かす手順をまとめたものです。

## 概要

- **実装場所**: `serverless/pytorch/openmmlab/mmdetection/rtmdet_s/nuclio/`
- **Nuclio 上の名前**: `pth-openmmlab-mmdetection-rtmdet-s`（UI 表示名は **RTMDet-s (MMDetection)**）
- **推論**: MMDetection 3.3.0、`mim download` で取得した `rtmdet_s_8xb32-300e_coco` の設定と重み
- **クラス**: COCO 80 クラス（MMDetection の `CocoDataset` と同じ表記。例: `traffic light`, `tv` など）

## 前提条件

1. **CVAT の Docker 環境**が起動していること（`docker compose up` 等）。
2. **サーバレス（Nuclio）を有効にする**構成。
   リポジトリでは `docker compose -f docker-compose.yml -f components/serverless/docker-compose.serverless.yml up -d` のように **serverless 用の compose を重ねる**方法が想定されています。
   これにより `CVAT_SERVERLESS=1` と、`cvat_server` / `cvat_worker_annotation` への `host.docker.internal` の付与が行われます。
3. **`nuctl`**（Nuclio CLI）がインストール済みであること。
   公式ドキュメントの [Automatic annotation](https://docs.cvat.ai/docs/administration/community/advanced/installation_automatic_annotation/) を参照。
4. **GPU 版**を使う場合は、NVIDIA ドライバ・Docker から GPU が利用できること。

## デプロイ手順（GPU 推奨）

CVAT リポジトリのルートで実行します。

```bash
./serverless/deploy_gpu.sh serverless/pytorch/openmmlab/mmdetection/rtmdet_s/nuclio
```

成功すると `nuctl get function` に `pth-openmmlab-mmdetection-rtmdet-s` が **ready** で表示されます。

### ビルドが止まる・権限エラーになる場合

環境によっては Docker BuildKit 周りで失敗することがあります。その場合は次のように **legacy ビルダー**を指定して実行します。

```bash
DOCKER_BUILDKIT=0 ./serverless/deploy_gpu.sh serverless/pytorch/openmmlab/mmdetection/rtmdet_s/nuclio
```

### デプロイが「既にプロビジョニング中」と言われる場合

前回のデプロイが途中で残っていると更新できません。次で強制削除してから再実行します。

```bash
nuctl delete function pth-openmmlab-mmdetection-rtmdet-s --platform local --force
DOCKER_BUILDKIT=0 ./serverless/deploy_gpu.sh serverless/pytorch/openmmlab/mmdetection/rtmdet_s/nuclio
```

## CPU のみで試す場合

```bash
./serverless/deploy_cpu.sh serverless/pytorch/openmmlab/mmdetection/rtmdet_s/nuclio
```

ビルドは重く、推論も遅いです。検証用途向けです。

## CVAT 画面での使い方

1. タスクを開き、**Actions → Automatic annotation**（または該当メニュー）を開く。
2. モデル一覧から **RTMDet-s (MMDetection)** を選択する。
3. ラベルマッピングとしきい値を設定して実行する。

## 技術的な補足（なぜこの構成か）

- **CVAT からの呼び出し**: `cvat_worker_annotation` が Nuclio 関数の **ホストポート**へ HTTP POST します。`docker-compose.serverless.yml` の `extra_hosts` により、`host.docker.internal` 経由でホスト上に公開されたポートに到達します。
- **イメージのビルド**: `function-gpu.yaml` の `directives` で PyTorch ベースイメージに **OpenMIM / mmcv / mmdet** を入れ、`mim download mmdet --config rtmdet_s_8xb32-300e_coco` で設定とチェックポイントを `/opt/nuclio` に配置します。
- **ランタイム依存**: OpenCV（mmcv）が参照する **X11 / GL 系の共有ライブラリ**、`numpy` と **PyTorch 2.1 系のバイナリ**の互換のため **`numpy<2`** を入れる、といった調整が `function-gpu.yaml` / `function.yaml` に含まれています。
- **入力画像**: CVAT はフレームを base64 で送ります。`main.py` では **OpenCV `imdecode`** でデコードし、動画フレーム由来の PNG などで PIL が失敗しやすいケースを避けています。

## トラブルシューティング

| 症状 | 確認・対処 |
|------|------------|
| 画面に「Automatic annotation failed」 | `docker logs cvat_worker_annotation --tail 80` で HTTP エラー・URL を確認。`docker logs nuclio-nuclio-pth-openmmlab-mmdetection-rtmdet-s --tail 80` でスタックトレースを確認。 |
| 関数コンテナが `Restarting` | 依存ライブラリ不足や `numpy` 2.x との不整合。`function-gpu.yaml` の `directives` と最新イメージの再ビルドを確認。 |
| デプロイが長時間かかる | 初回は `mim` によるパッケージ取得・重みダウンロードで時間がかかります。 |
| `docker build` の permission denied | `~/.docker/buildx` の権限、または `DOCKER_BUILDKIT=0` で再実行。 |

## 関連ファイル

| パス | 内容 |
|------|------|
| `serverless/pytorch/openmmlab/mmdetection/rtmdet_s/nuclio/main.py` | ハンドラ（推論・JSON 応答） |
| `serverless/pytorch/openmmlab/mmdetection/rtmdet_s/nuclio/function-gpu.yaml` | GPU 用 Nuclio 定義 |
| `serverless/pytorch/openmmlab/mmdetection/rtmdet_s/nuclio/function.yaml` | CPU 用 Nuclio 定義 |
| `serverless/deploy_gpu.sh` / `serverless/deploy_cpu.sh` | デプロイスクリプト |
| `components/serverless/docker-compose.serverless.yml` | サーバレス有効化用 compose フラグメント |

## 参考

- [MMDetection](https://github.com/open-mmlab/mmdetection)
- [CVAT: Automatic annotation](https://docs.cvat.ai/docs/administration/community/advanced/installation_automatic_annotation/)
