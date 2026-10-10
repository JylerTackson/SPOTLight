import cv2
import numpy as np
from readers.gauge import read

def test_calibrated_needle():
    image=np.full((240,240,3),255,np.uint8)
    cv2.circle(image,(120,120),100,(0,0,0),2)
    cv2.line(image,(120,120),(120,55),(0,0,0),4)
    result=read(image,[],dict(unit='psi',min_value=0,max_value=200,theta_min_deg=135,theta_max_deg=405))
    assert abs(result['value']-100)<6
