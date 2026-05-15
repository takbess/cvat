## Serverless for Computer Vision Annotation Tool (CVAT)

### Run docker container

```bash
# From project root directory
# 基本はこちら
docker compose -f docker-compose.yml -f components/serverless/docker-compose.serverless.yml up -d
# WSL2の時
docker compose -f docker-compose.yml \
  -f components/serverless/docker-compose.serverless.yml \
  -f docker-compose.lambda-wsl2.yml up -d
```
