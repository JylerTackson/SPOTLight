"""Circular dial reader with ray-darkness ambiguity and explicit calibration provenance."""
import json
from pathlib import Path
import cv2
import numpy as np
from textaxes import parse_num, calibrate_axis
VERSION = 'gauge-1.0'

def read(image, words, calibration=None, asset_id=None):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h,w = gray.shape
    circles = cv2.HoughCircles(cv2.GaussianBlur(gray,(5,5),1), cv2.HOUGH_GRADIENT,
                              dp=1, minDist=min(h,w)/2, param1=100, param2=25,
                              minRadius=int(min(h,w)*.25), maxRadius=int(min(h,w)*.49))
    if circles is None:
        return dict(value=None, confidence=0., flags=['UNREADABLE'], needle=None, unit='psi')
    cx,cy,r = min(circles[0],key=lambda c: (c[0]-w/2)**2+(c[1]-h/2)**2)
    angles=np.arange(0,360,.5); rr=np.linspace(r*.18,r*.68,80)
    rad=np.deg2rad(angles)
    xs=np.clip(np.rint(cx+np.cos(rad[:,None])*rr).astype(int),0,w-1)
    ys=np.clip(np.rint(cy+np.sin(rad[:,None])*rr).astype(int),0,h-1)
    scores=np.mean((255-gray[ys,xs])/255,axis=1)
    best=int(scores.argmax()); angle=float(angles[best])
    separation=np.abs((angles-angle+180)%360-180)>18
    second=float(scores[separation].max()); ratio=float(scores[best]/max(second,.01))
    flags=[]; confidence=.85
    if ratio<1.35:
        flags.append('AMBIGUOUS_NEEDLE'); confidence=.35
    if scores[best]<.25:
        flags.append('UNREADABLE'); confidence=.2
    # Unwrap label angles into the standard clockwise 135..405 sweep.
    ticks=[]
    for word in words:
        number=parse_num(word['text']); q=np.mean(word['quad'],axis=0)
        distance=np.hypot(q[0]-cx,q[1]-cy)
        if number is not None and r*.5<distance<r*1.1:
            theta=float(np.degrees(np.arctan2(q[1]-cy,q[0]-cx))%360)
            if theta<110: theta+=360
            ticks.append((theta,number))
    fit=calibrate_axis(ticks,threshold=8)
    if fit and fit[0]>0:
        a,b,inliers=fit
        if not all(inliers): flags.append('SCALE_LABEL_INCONSISTENT'); confidence=min(confidence,.45)
        angle=angle+360 if angle<110 else angle
        value=a*angle+b; unit='psi'
    else:
        # Even with too few inliers, non-monotonic labels are evidence of a bad scale.
        ordered=sorted(ticks)
        if any(y[1]<=x[1] for x,y in zip(ordered,ordered[1:])):
            flags.append('SCALE_LABEL_INCONSISTENT'); confidence=min(confidence,.45)
        if calibration is None and asset_id:
            calibration=json.loads((Path(__file__).parents[1]/'config/gauges.json').read_text()).get(asset_id)
        if calibration is None:
            calibration=dict(unit='psi', min_value=0,max_value=200,theta_min_deg=135,theta_max_deg=405)
            flags.append('DEFAULT_CALIBRATION'); confidence=min(confidence,.4)
        start=calibration['theta_min_deg']; end=calibration['theta_max_deg']
        angle=start+(angle-start)%360
        if angle>end+5:
            flags.append('UNREADABLE'); confidence=min(confidence,.2)
        value=calibration['min_value']+(angle-start)/(end-start)*(calibration['max_value']-calibration['min_value'])
        unit=calibration['unit']
    tip=[float(cx+np.cos(np.deg2rad(angle))*r*.68),float(cy+np.sin(np.deg2rad(angle))*r*.68)]
    return dict(value=round(float(value),2),confidence=confidence,flags=flags,needle=[[float(cx),float(cy)],tip],unit=unit,peak_ratio=ratio)
