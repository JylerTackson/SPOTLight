# Reader evaluation

Run on CPU: {"host": "AsusG14", "platform": "Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.43", "processor": "", "device": "CPU", "python": "3.12.14"}

150 deterministic synthetic images; mission splits from System 1 manifest. These are synthetic checks, not real-world accuracy.
Null measurements are excluded from numerical MAE; measurable counts, low-confidence rate and abstentions are reported separately. Agreement accuracy over all twins counts abstentions as failures; decided accuracy includes only non-null decisions. Latencies include OCR and annotation, cache cleared before every render.

## train

```json
{
  "PRESSURE_PSI": {
    "count": 47,
    "measurable_count": 44,
    "low_confidence_rate": 0.14893617021276595,
    "agrees_accuracy_all_twins": 0.9090909090909091,
    "agrees_coverage": 0.9090909090909091,
    "agrees_accuracy_decided": 1.0,
    "unreadable_correctly_flagged_rate": 1.0,
    "agrees_accuracy_by_variant": {
      "true": 0.9090909090909091,
      "perturbed": 0.9090909090909091
    },
    "latency_p50_ms": 220.06,
    "latency_p95_ms": 302.14099999999985,
    "mae_percent_fs": 0.28756983474029174,
    "within_2_percent_fs": 1.0
  },
  "TEMPERATURE_C": {
    "count": 55,
    "measurable_count": 50,
    "low_confidence_rate": 0.09090909090909091,
    "agrees_accuracy_all_twins": 1.0,
    "agrees_coverage": 1.0,
    "agrees_accuracy_decided": 1.0,
    "unreadable_correctly_flagged_rate": 1.0,
    "agrees_accuracy_by_variant": {
      "true": 1.0,
      "perturbed": 1.0
    },
    "latency_p50_ms": 331.36,
    "latency_p95_ms": 379.637,
    "max_temperature_mae_c": 0.637126559134722,
    "hotspot_center_error_px": 1.487322337216625
  }
}
```

## heldout

```json
{
  "PRESSURE_PSI": {
    "count": 17,
    "measurable_count": 16,
    "low_confidence_rate": 0.23529411764705882,
    "agrees_accuracy_all_twins": 0.8125,
    "agrees_coverage": 0.8125,
    "agrees_accuracy_decided": 1.0,
    "unreadable_correctly_flagged_rate": 1.0,
    "agrees_accuracy_by_variant": {
      "true": 1.0,
      "perturbed": 0.625
    },
    "latency_p50_ms": 216.0,
    "latency_p95_ms": 240.10399999999998,
    "mae_percent_fs": 0.2138820882506691,
    "within_2_percent_fs": 1.0
  },
  "TEMPERATURE_C": {
    "count": 31,
    "measurable_count": 30,
    "low_confidence_rate": 0.03225806451612903,
    "agrees_accuracy_all_twins": 1.0,
    "agrees_coverage": 1.0,
    "agrees_accuracy_decided": 1.0,
    "unreadable_correctly_flagged_rate": 1.0,
    "agrees_accuracy_by_variant": {
      "true": 1.0,
      "perturbed": 1.0
    },
    "latency_p50_ms": 335.15,
    "latency_p95_ms": 385.21500000000003,
    "max_temperature_mae_c": 0.6114666033699988,
    "hotspot_center_error_px": 4.0573129825874705
  }
}
```

## Kit samples (eval/demo only)

- acoustic_valve_01.jpg: {"router": {"modality": "unsupported", "source": "action_type"}, "vision": []}
- gauge_pressure_01.jpg: {"router": {"modality": "gauge", "source": "action_type"}, "vision": [{"id": "V1", "tool": "vision.gauge", "quantity": "pressure", "value": -1.71, "unit": "psi", "confidence": 0.45, "trust": "low", "flags": ["SCALE_LABEL_INCONSISTENT"], "logged_id": null, "logged_value": null, "delta": null, "agrees": null, "pairing": "demo"}]}
- pipe_gallery_01.jpg: {"router": {"modality": "unsupported", "source": "action_type"}, "vision": []}
- thermal_pump_bearing_01.jpg: {"router": {"modality": "thermal", "source": "action_type"}, "vision": [{"id": "V1", "tool": "vision.thermal", "quantity": "max_temperature", "value": 100.97, "unit": "°C", "confidence": 0.8, "trust": "high", "flags": ["CLIPPED"], "logged_id": null, "logged_value": null, "delta": null, "agrees": null, "pairing": "demo"}, {"id": "V2", "tool": "vision.thermal", "quantity": "reference_temperature", "value": 41.73, "unit": "°C", "confidence": 0.8, "trust": "high", "flags": ["CLIPPED"], "logged_id": null, "logged_value": null, "delta": null, "agrees": null, "pairing": "demo"}, {"id": "V3", "tool": "vision.thermal", "quantity": "delta_temperature", "value": 59.24, "unit": "°C", "confidence": 0.8, "trust": "high", "flags": ["CLIPPED"], "logged_id": null, "logged_value": null, "delta": null, "agrees": null, "pairing": "demo"}]}
- valve_detail_01.jpg: {"router": {"modality": "unsupported", "source": "action_type"}, "vision": []}
- visual_pump_motor_01.jpg: {"router": {"modality": "unsupported", "source": "action_type"}, "vision": []}

Acoustic and visual scenes return unsupported modality: their readers are out of scope. VLM calls are reserved and unused. OCR inference is offline using bundled RapidOCR models. Real-world accuracy remains unverified.
