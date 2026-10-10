# Vision service v1 (:8084)

CPU code computes measurements; the VLM only explains. All images are base64 JPEG/PNG
(without a data URI). GET /health returns `{status, versions: {service, readers, ocr}}`.

POST /v1/vision accepts `{image_b64, action_type?, asset_id?, logged?, calibration?, pairing?}`.
`action_type` is THERMAL_INSPECTION or GAUGE_READING; other actions return an unsupported
modality with empty readings. Without it, ≥81% saturated scene pixels selects thermal,
otherwise gauge. `logged` is `{reading_id, measurement_type, value, unit}`.
`calibration` is `{unit, min_value, max_value, theta_min_deg, theta_max_deg}`;
angles increase clockwise in image coordinates, zero pointing right, and may exceed 360.
`pairing` is demo (default, including kit samples) or synthetic (caller explicitly identifies renders).
No kit image is linked to a CSV row: demo pairing is illustrative only.

Response fields: `router: {modality, source: action_type|heuristic}`, Orbit-style
`key_results: [{name, units, value}]`, `vision`, `ocr: [{text, conf, quad}]`,
`alert: {title, severity: 0..4, source}|null`, `annotated_image_b64`, `versions`, `latency_ms`.
Quad coordinates and annotations refer to the downscaled image (longest side ≤1280).

Each vision row has exactly these fields:
```json
{"id":"V1","tool":"vision.thermal","quantity":"max_temperature","value":99.8,"unit":"°C","confidence":0.8,"trust":"high","flags":["CLIPPED"],"logged_id":"R0042","logged_value":83.5,"delta":16.3,"agrees":false,"pairing":"demo"}
```
Absent measurement/log/comparable units yields null value/delta/agrees as applicable.
Confidence <0.5 means low trust and null agrees. Otherwise trust is high and
`agrees = abs(delta) <= tolerance`: VISION_THERMAL_TOLERANCE_C=4,
VISION_GAUGE_TOLERANCE_PSI=6. Non-psi gauge comparisons remain null.
Low-trust rows must never be stated as fact downstream. Thermal reference and delta-T
rows have no logged pairing; only the maximum is compared. Flags include CLIPPED,
UNREADABLE, SCALE_LABEL_INCONSISTENT, AMBIGUOUS_NEEDLE and DEFAULT_CALIBRATION.
Alerts request manual review for unreadable or disagreeing evidence; they are not equipment safety thresholds.

POST /v1/ocr accepts `{image_b64}` and returns `{ocr: [...]}`.
400: malformed base64 or undecodable image. 413: original decoded dimensions exceed
VISION_MAX_PIXELS (default 16000000), checked before resizing or pixel allocation.
422: malformed request fields. Images first undergo this size guard, then downscaling.

Reader extraction is cached in a bounded in-process LRU by SHA256(image bytes), reader
versions, modality, asset and calibration. Logged comparisons and annotation responses
are computed per request so cache entries never reuse another log's agreement.

## Feeding System 2 (proposal)
The owner may render vision[] as citable V# rows, keeping confidence, flags, pairing,
logged_id and agrees. OCR words can receive O# IDs, clearly labelled OCR observations.
Send the annotated image with those rows; low trust requires an unreadable/manual-check
statement. System 2's owner decides its final packet and schema; this service changes neither.
