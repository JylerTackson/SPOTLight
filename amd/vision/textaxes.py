"""CPU OCR and robust numeric axis calibration; no network or VLM calls."""
import re
import threading
from functools import lru_cache
import cv2
import numpy as np
from sklearn.linear_model import LinearRegression, RANSACRegressor

_LOCK = threading.Lock()

@lru_cache(maxsize=1)
def engine():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)

def ocr(image):
    factor = 3 if image.shape[0] < 300 else 1
    with _LOCK:
        result, _ = engine()(cv2.resize(image, None, fx=factor, fy=factor))
    return [{"text": text, "conf": float(conf), "quad": (np.asarray(quad)/factor).tolist()}
            for quad, text, conf in (result or [])]

def parse_num(text):
    text = text.strip().replace('−', '-').replace('O', '0').replace('S', '5')
    match = re.fullmatch(r'\s*([+-]?\d+(?:\.\d+)?)\s*(?:°?[CF]|psi)?\s*', text, re.I)
    return float(match[1]) if match else None

def calibrate_axis(ticks, threshold=3):
    if len(ticks) < 3:
        return None
    points = np.asarray(ticks, dtype=float)
    if np.ptp(points[:, 0]) < 1e-6:
        return None
    model = RANSACRegressor(LinearRegression(), min_samples=2,
                           residual_threshold=threshold, random_state=0)
    try:
        model.fit(points[:, :1], points[:, 1])
    except ValueError:
        return None
    if model.inlier_mask_.sum() < 3:
        return None
    return float(model.estimator_.coef_[0]), float(model.estimator_.intercept_), model.inlier_mask_.tolist()
