import base64
import binascii
import hashlib
import io
import json
import time
from functools import lru_cache
from typing import Literal
import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
import config
from textaxes import ocr
from readers import thermal, gauge
from annotate import annotate

VERSIONS=dict(service=config.SERVICE_VERSION,readers=f'{thermal.VERSION}/{gauge.VERSION}',ocr='rapidocr-onnxruntime-1.4.4')
app=FastAPI(title='SPOT vision',version=config.SERVICE_VERSION)
class Logged(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False)
    reading_id:str
    measurement_type:str
    value:float
    unit:str
class Calibration(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False)
    unit:str
    min_value:float
    max_value:float
    theta_min_deg:float=135
    theta_max_deg:float=405
    @model_validator(mode='after')
    def ordered(self):
        if self.max_value<=self.min_value or not 0<self.theta_max_deg-self.theta_min_deg<=360:
            raise ValueError('calibration requires increasing values and an angle sweep in (0,360]')
        return self
class ImageRequest(BaseModel):
    image_b64:str
class VisionRequest(ImageRequest):
    action_type:str|None=None
    asset_id:str|None=None
    logged:Logged|None=None
    calibration:Calibration|None=None
    pairing:Literal['demo','synthetic']='demo'

def decode(encoded):
    try:
        data=base64.b64decode(encoded,validate=True)
        with Image.open(io.BytesIO(data)) as source:
            if source.width*source.height>config.MAX_PIXELS:
                raise HTTPException(413,'image exceeds VISION_MAX_PIXELS')
            source.thumbnail((1280,1280))
            rgb=np.asarray(source.convert('RGB'))
        return cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR),data
    except HTTPException:raise
    except Image.DecompressionBombError as exc:
        raise HTTPException(413,'image exceeds VISION_MAX_PIXELS') from exc
    except (ValueError,binascii.Error,UnidentifiedImageError,OSError) as exc:
        raise HTTPException(400,'bad or undecodable image') from exc

def normalize_unit(unit):
    unit = unit.strip().casefold()
    return "°C" if unit in {"c", "°c", "degc", "celsius"} else unit

def row(result,quantity,unit,logged=None,pairing='demo',index=1):
    value=result['value'];conf=result['confidence']
    canonical_unit=normalize_unit(unit)
    comparable=logged is not None and ((canonical_unit=='°C' and logged.measurement_type=='TEMPERATURE_C' and normalize_unit(logged.unit)=="°C") or
                                      (canonical_unit=='psi' and logged.measurement_type=='PRESSURE_PSI' and normalize_unit(logged.unit)=='psi'))
    delta=round(value-logged.value,2) if value is not None and comparable else None
    tolerance=config.THERMAL_TOLERANCE if canonical_unit=='°C' else config.GAUGE_TOLERANCE
    return dict(id=f'V{index}',tool=f"vision.{'thermal' if canonical_unit=='°C' else 'gauge'}",quantity=quantity,value=value,unit=unit,
                confidence=conf,trust='high' if conf>=.5 else 'low',flags=result['flags'],
                logged_id=logged.reading_id if logged else None,logged_value=logged.value if logged else None,
                delta=delta,agrees=abs(delta)<=tolerance if delta is not None and conf>=.5 else None,pairing=pairing)

@lru_cache(maxsize=config.CACHE_SIZE)
def extract(digest,reader_versions,modality,calibration_json,asset_id,image_bytes):
    # digest and versions are explicit cache components; bytes retained only in bounded LRU.
    image,_=decode(base64.b64encode(image_bytes).decode())
    words=ocr(image)
    cal=json.loads(calibration_json) if calibration_json else None
    result=(thermal if modality=='thermal' else gauge).read(image,words,cal,asset_id) if modality!='unsupported' else None
    return words,result

@app.get('/health')
def health():return dict(status='ok',versions=VERSIONS)
@app.post('/v1/ocr')
def read_ocr(request:ImageRequest):
    image,_=decode(request.image_b64)
    return dict(ocr=ocr(image))
@app.post('/v1/vision')
def vision(request:VisionRequest):
    start=time.perf_counter();image,data=decode(request.image_b64)
    if request.action_type:
        modality={'THERMAL_INSPECTION':'thermal','GAUGE_READING':'gauge'}.get(request.action_type,'unsupported');source='action_type'
    else:
        saturated=np.mean(cv2.cvtColor(image,cv2.COLOR_BGR2HSV)[:,:,1]>80)
        modality='thermal' if saturated>=.81 else 'gauge';source='heuristic'
    cal=request.calibration.model_dump_json() if request.calibration else ''
    words,result=extract(hashlib.sha256(data).hexdigest(),VERSIONS['readers'],modality,cal,request.asset_id,data)
    rows=[];alert=None
    if result:
        unit='°C' if modality=='thermal' else result['unit']
        rows=[row(result,'max_temperature' if modality=='thermal' else 'pressure',unit,request.logged,request.pairing)]
        if modality=='thermal' and result.get('reference') is not None:
            for index,(quantity,key) in enumerate([('reference_temperature','reference'),('delta_temperature','delta_t')],2):
                rows.append(row(dict(result,value=result[key]),quantity,unit,pairing=request.pairing,index=index))
        if result['confidence']<.5:alert=dict(title='Image unreadable; manual review required',severity=1,source='vision')
        elif rows[0]['agrees'] is False:alert=dict(title='Image and log disagree; manual check required',severity=2,source='vision')
    return dict(router=dict(modality=modality,source=source),key_results=[dict(name=r['quantity'],units=r['unit'],value=r['value']) for r in rows],
                vision=rows,ocr=words,alert=alert,annotated_image_b64=annotate(image,result or {},modality),versions=VERSIONS,
                latency_ms=round((time.perf_counter()-start)*1000,2))
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host=config.HOST,port=config.PORT,log_level=config.LOG_LEVEL)
