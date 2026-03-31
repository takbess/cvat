# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

import base64
import json
from pathlib import Path

import cv2
import numpy as np
import torch

from mmdet.apis import init_detector, inference_detector
from mmdet.utils import register_all_modules


def _parse_event_body(body):
    if isinstance(body, (bytes, bytearray)):
        return json.loads(body.decode("utf-8"))
    if isinstance(body, str):
        return json.loads(body)
    return body


def _decode_image_bgr(image_b64: str) -> np.ndarray:
    raw = base64.b64decode(image_b64, validate=False)
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("cannot decode image bytes (cv2.imdecode returned None)")
    return img


def _find_assets(work_dir: Path) -> tuple[str, str]:
    configs = sorted(work_dir.glob("yolox_s_8x8_300e_coco.py"))
    ckpts = sorted(work_dir.glob("yolox_s_8x8_300e_coco*.pth"))
    if not configs or not ckpts:
        raise RuntimeError(
            f"Missing YOLOX config or checkpoint in {work_dir}. "
            f"configs={configs}, ckpts={ckpts}"
        )
    return str(configs[0]), str(ckpts[0])


def init_context(context):
    context.logger.info("Init context...  0%")
    register_all_modules()

    config_file, checkpoint_file = _find_assets(Path("/opt/nuclio"))
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    model = init_detector(config_file, checkpoint_file, device=device)
    context.user_data.model = model

    context.logger.info("Init context...100%")


def handler(context, event):
    context.logger.info("Run MMDetection YOLOX-s model")
    data = _parse_event_body(event.body)
    threshold = float(data.get("threshold", 0.5))
    # CVAT sends raw base64 (see LambdaFunction._get_image). Prefer OpenCV decode:
    # some frames decode fine with cv2 but fail in PIL (UnidentifiedImageError).
    img = _decode_image_bgr(data["image"])

    model = context.user_data.model
    result = inference_detector(model, img)
    pred_instances = result.pred_instances

    classes = model.dataset_meta["classes"]
    h, w = img.shape[:2]

    results = []
    if len(pred_instances) > 0:
        bboxes = pred_instances.bboxes.cpu().numpy()
        scores = pred_instances.scores.cpu().numpy()
        labels = pred_instances.labels.cpu().numpy().astype(int)

        for box, score, label_idx in zip(bboxes, scores, labels):
            if float(score) < threshold:
                continue
            xtl, ytl, xbr, ybr = box
            xtl = max(int(xtl), 0)
            ytl = max(int(ytl), 0)
            xbr = min(int(xbr), w)
            ybr = min(int(ybr), h)
            label_name = classes[int(label_idx)]
            results.append(
                {
                    "confidence": str(float(score)),
                    "label": label_name,
                    "points": [xtl, ytl, xbr, ybr],
                    "type": "rectangle",
                }
            )

    return context.Response(
        body=json.dumps(results), headers={}, content_type="application/json", status_code=200
    )
