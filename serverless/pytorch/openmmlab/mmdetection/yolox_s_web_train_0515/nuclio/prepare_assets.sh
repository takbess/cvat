#!/usr/bin/env bash
# Sync MMDetection config, last_checkpoint, and the referenced .pth into this directory
# so nuctl deploy includes them in the function image (under /opt/nuclio).
set -euo pipefail

HERE="$(cd "$(dirname "${0}")" && pwd)"
REPO_ROOT="$(cd "${HERE}/../../../../../../../.." && pwd)"
WORK_DIR="${REPO_ROOT}/work_dirs/web_train_2026_0515_0011_3857fe45"

if [[ ! -d "${WORK_DIR}" ]]; then
  echo "error: work dir not found: ${WORK_DIR}" >&2
  exit 1
fi
if [[ ! -f "${WORK_DIR}/yolox_s_finetune.py" ]]; then
  echo "error: missing ${WORK_DIR}/yolox_s_finetune.py" >&2
  exit 1
fi
if [[ ! -f "${WORK_DIR}/last_checkpoint" ]]; then
  echo "error: missing ${WORK_DIR}/last_checkpoint" >&2
  exit 1
fi

cp -f "${WORK_DIR}/yolox_s_finetune.py" "${HERE}/"

RAW="$(tr -d '\r\n' < "${WORK_DIR}/last_checkpoint")"
if [[ -z "${RAW}" ]]; then
  echo "error: empty ${WORK_DIR}/last_checkpoint" >&2
  exit 1
fi

# MMEngine may store either a basename or an absolute path. Stage under /opt/nuclio with a
# basename-only last_checkpoint so the Nuclio image stays self-contained.
if [[ "${RAW}" = /* ]]; then
  SRC="${RAW}"
  CKPT_BASE="$(basename "${RAW}")"
else
  SRC="${WORK_DIR}/${RAW}"
  CKPT_BASE="${RAW}"
fi
if [[ ! -f "${SRC}" ]]; then
  echo "error: checkpoint file missing: ${SRC}" >&2
  exit 1
fi

cp -f "${SRC}" "${HERE}/${CKPT_BASE}"
printf '%s\n' "${CKPT_BASE}" > "${HERE}/last_checkpoint"
echo "Prepared assets in ${HERE}: yolox_s_finetune.py, last_checkpoint -> ${CKPT_BASE}"
