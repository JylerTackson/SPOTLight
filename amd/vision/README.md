# CPU vision service

FastAPI on :8084, RapidOCR with bundled ONNX models, code thermal and gauge readers.
Code computes numbers; VLM integration is reserved and unused in phase 1.
See [HTTP contract](../../docs/vision-contract.md) and [running guide](../../docs/RUNNING.md).

From repo root:
```bash
make vision-venv
make test-vision
amd/vision/.venv/bin/python amd/vision/app.py
```

Generate reproducible CSV-derived images plus actual service responses:
```bash
amd/vision/.venv/bin/python amd/vision/scripts/render_synth.py --with-vision-rows --service-url http://127.0.0.1:8084
amd/vision/.venv/bin/python amd/vision/scripts/eval_readers.py
```

The manifest partitions by mission. Never train on heldout missions or kit images.
150 small JPEGs are committed; renderer SHA1 seeds include reading ID and variant.
Identical dependency versions and fonts are needed for
byte reproduction. Numerical MAE is measured on readable true/perturbed renders,
including low-confidence estimates; missing values and unreadable cases are reported separately.

Gauge calibration: OCR RANSAC, request calibration, config/gauges.json, default
270-degree sweep (low confidence). Per-asset calibration can be mounted read-only
at `/app/config/gauges.json`; restart after changes to invalidate the LRU.
Thermal reads an observed bar; it cannot measure an image without numeric scale
unless explicit calibration is supplied. Ironbow here is a documented synthetic
palette, not a camera radiometric calibration. Both readers abstain on failed detection.
Unsupported actions return no V# readings. Acoustic/path readers and GPU fine-tuning
are outside phase 1. Demo log pairing is illustrative, since the kit supplies no image-to-row links.

Environment variables (only runtime configuration): VISION_HOST, VISION_PORT,
VISION_MAX_PIXELS, VISION_THERMAL_TOLERANCE_C, VISION_GAUGE_TOLERANCE_PSI,
VISION_CACHE_SIZE, VISION_LOG_LEVEL, VISION_LLAMA_URL (unused).
Image uploads are checked against original pixel dimensions then resized ≤1280.
The bounded LRU stores extracted results, never request-specific log comparisons.
