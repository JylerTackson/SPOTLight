"""Invert an observed thermal colour bar; missing calibration is never invented."""
import cv2
import numpy as np
from textaxes import parse_num, calibrate_axis

VERSION = 'thermal-1.1'

def read(image, words, calibration=None, asset_id=None):
    h, w = image.shape[:2]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # A narrow vertical column with many saturated colours is the bar.
    mask = (hsv[:, :, 1] > 80) & (hsv[:, :, 2] > 50)
    candidates = []
    for x in range(int(w*.7), w-3):
        ys = np.flatnonzero(mask[:, x])
        if len(ys) > h*.45:
            candidates.append((len(np.unique(image[ys, x]//16, axis=0)), x, ys))
    if not candidates:
        return dict(value=None, confidence=0., flags=['UNREADABLE'], box=None, reference=None, delta_t=None)
    _, x, ys = max(candidates, key=lambda item: item[0])
    y0, y1 = int(ys[0])+2, int(ys[-1])-2
    lut = np.median(image[y0:y1+1, max(0,x-1):x+2], axis=1).astype(float)
    ticks = []
    for word in words:
        n = parse_num(word['text'])
        q = np.mean(word['quad'], axis=0)
        if n is not None and q[0] > x and y0-20 < q[1] < y1+20:
            ticks.append((q[1], n))
    fit = calibrate_axis(ticks, threshold=3)
    if fit:
        a, b, _ = fit
    elif len(ticks) >= 2:
        lo, hi = min(ticks), max(ticks)
        if hi[0]-lo[0] < 10:
            return dict(value=None, confidence=0., flags=['UNREADABLE'], box=None, reference=None, delta_t=None)
        a = (hi[1]-lo[1])/(hi[0]-lo[0]); b = lo[1]-a*lo[0]
    elif calibration:
        a = (calibration['min_value']-calibration['max_value'])/(y1-y0)
        b = calibration['max_value']-a*y0
    else:
        return dict(value=None, confidence=0., flags=['UNREADABLE'], box=None, reference=None, delta_t=None)
    # Chunk distances to avoid N-pixels x LUT memory blowups on uploads.
    scene = image[:, :max(1,x-12)]
    pixels = scene.reshape(-1,3).astype(float)
    indices=[]; distances=[]
    for chunk in np.array_split(pixels, max(1,len(pixels)//2048+1)):
        d = ((chunk[:,None,:]-lut[None,:,:])**2).sum(axis=2)
        indices.extend(d.argmin(axis=1)); distances.extend(d.min(axis=1))
    values = (a*(np.asarray(indices)+y0)+b).reshape(scene.shape[:2]).astype(np.float32)
    valid = (np.asarray(distances).reshape(values.shape)<65**2) & (hsv[:,:scene.shape[1],1]>45)
    weights = cv2.blur(valid.astype(np.float32), (5,5))
    values = cv2.blur(np.where(valid, values, 0), (5,5))/np.maximum(weights, .001)
    valid &= weights > .85
    valid[:5] = False; valid[-5:] = False; valid[:, :5] = False; valid[:, -5:] = False
    if valid.mean()<.15:
        return dict(value=None, confidence=0., flags=['UNREADABLE'], box=None, reference=None, delta_t=None)
    maximum = float(np.max(values[valid]))
    hot = ((values>=maximum-3)&valid).astype(np.uint8)
    count, labels, stats, centers = cv2.connectedComponentsWithStats(hot)
    i = 1+np.argmax(stats[1:,cv2.CC_STAT_AREA])
    xx, yy, ww, hh, area = stats[i]
    reference = float(np.median(values[valid & (labels!=i)])) if np.any(valid & (labels!=i)) else maximum
    clipped = maximum >= max(a*y0+b,a*y1+b)-1.5
    return dict(value=round(maximum,2), confidence=.8 if area>=8 else .35,
                flags=['CLIPPED'] if clipped else [], box=[int(xx),int(yy),int(ww),int(hh)],
                reference=round(reference,2), delta_t=round(maximum-reference,2))
