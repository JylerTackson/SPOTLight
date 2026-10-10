import base64
import cv2

def annotate(image, result, modality):
    image=image.copy()
    if result.get('box'):
        x,y,w,h=result['box'];cv2.rectangle(image,(x,y),(x+w,y+h),(0,255,0),2)
    if result.get('needle'):
        start,end=result['needle'];cv2.line(image,tuple(map(int,start)),tuple(map(int,end)),(0,0,255),2)
    if result:
        cv2.putText(image,f"V1 {result.get('value')} {'C' if modality=='thermal' else result.get('unit','psi')}",
                (5,15),cv2.FONT_HERSHEY_SIMPLEX,.4,(0,255,0),1)
    if modality=='thermal' and result.get('reference') is not None:
        cv2.putText(image,f"V2 ref {result['reference']} C / V3 dT {result['delta_t']} C",(5,30),cv2.FONT_HERSHEY_SIMPLEX,.35,(0,255,0),1)
    ok,data=cv2.imencode('.jpg',image)
    if not ok:raise ValueError('annotation encoding failed')
    return base64.b64encode(data).decode()
