import base64
import io
import json
from pathlib import Path
import pytest
from PIL import Image
from fastapi.testclient import TestClient
import app
from scripts.render_synth import render
client=TestClient(app.app)
ROOT=Path(__file__).resolve().parents[3]

def encoded(measurement='TEMPERATURE_C',value=70,variant='true'):
    data,_,cal,_=render('test1',variant,measurement,value)
    return base64.b64encode(data).decode(),cal

def test_contract_and_errors(monkeypatch):
    assert client.get('/health').json()['versions']['service']
    assert client.post('/v1/vision',json={'image_b64':'!'}).status_code==400
    assert client.post('/v1/ocr',json={'image_b64':base64.b64encode(b'garbage').decode()}).status_code==400
    monkeypatch.setattr(app.config,'MAX_PIXELS',10)
    b64,_=encoded()
    assert client.post('/v1/vision',json={'image_b64':b64}).status_code==413

@pytest.mark.parametrize('confidence,delta,expected',[(.49,0,None),(.5,4,True),(.8,4.01,False)])
def test_agrees(confidence,delta,expected):
    result=app.row(dict(value=70+delta,confidence=confidence,flags=[]),'max_temperature','°C',app.Logged(reading_id='R1',measurement_type='TEMPERATURE_C',value=70,unit='C'))
    assert result['agrees'] is expected
    assert result['trust']==('low' if confidence<.5 else 'high')

def test_gauge_tolerance_and_wrong_units():
    result=dict(value=106,confidence=.8,flags=[])
    logged=app.Logged(reading_id='R1',measurement_type='PRESSURE_PSI',value=100,unit='psi')
    assert app.row(result,'pressure','psi',logged)['agrees'] is True
    logged.unit='bar'
    assert app.row(result,'pressure','psi',logged)['agrees'] is None

@pytest.mark.parametrize('measurement,value,tolerance',[('TEMPERATURE_C',55,5),('TEMPERATURE_C',80,5),('PRESSURE_PSI',75,10),('PRESSURE_PSI',140,10)])
def test_render_readings(measurement,value,tolerance):
    b64,cal=encoded(measurement,value)
    response=client.post('/v1/vision',json=dict(image_b64=b64,calibration=cal,action_type='THERMAL_INSPECTION' if measurement=='TEMPERATURE_C' else 'GAUGE_READING',pairing='synthetic'))
    assert response.status_code==200
    body=response.json();row=body['vision'][0]
    assert abs(row['value']-value)<=tolerance
    assert set(row)=={'id','tool','quantity','value','unit','confidence','trust','flags','logged_id','logged_value','delta','agrees','pairing'}
    assert body['key_results'] and body['annotated_image_b64']

def test_cache_does_not_reuse_logs():
    b64,cal=encoded()
    payload=dict(image_b64=b64,calibration=cal,action_type='THERMAL_INSPECTION',logged=dict(reading_id='R1',measurement_type='TEMPERATURE_C',value=70,unit='C'))
    first=client.post('/v1/vision',json=payload).json()['vision'][0]
    payload['logged']['value']=30;payload['logged']['reading_id']='R2'
    second=client.post('/v1/vision',json=payload).json()['vision'][0]
    assert first['agrees'] is True and second['agrees'] is False
    assert second['logged_id']=='R2'

def test_kit_expectations():
    folder=ROOT/'SPOTDATA/SPOT_KnightHacks_Challenge_Kit Part One/04_ASSETS/sample_inspection_images'
    for name,action in [('thermal_pump_bearing_01.jpg','THERMAL_INSPECTION'),('gauge_pressure_01.jpg','GAUGE_READING')]:
        response=client.post('/v1/vision',json=dict(image_b64=base64.b64encode((folder/name).read_bytes()).decode(),action_type=action)).json()
        row=response['vision'][0]
        if name.startswith('thermal'):assert 'CLIPPED' in row['flags']
        else:assert row['confidence']<.5 or 'SCALE_LABEL_INCONSISTENT' in row['flags']

def test_unreadable_and_ocr():
    b64,cal=encoded(variant='unreadable')
    body=client.post('/v1/vision',json=dict(image_b64=b64,calibration=cal,action_type='THERMAL_INSPECTION')).json()
    assert body['vision'][0]['trust']=='low'
    assert client.post('/v1/ocr',json=dict(image_b64=b64)).json()=={'ocr':[]}

def test_split_manifest():
    heldout=set(json.loads((ROOT/'amd/system1/data/manifest.json').read_text())['holdout_missions'])
    for row in map(json.loads,(ROOT/'amd/vision/data/synth/manifest.jsonl').read_text().splitlines()):
        assert (row['split']=='heldout')==(row['mission_id'] in heldout)

@pytest.mark.parametrize('unit',['C','°C','degC','celsius','CELSIUS'])
def test_celsius_unit_normalization(unit):
    measured=dict(value=70,confidence=.8,flags=[])
    logged=app.Logged(reading_id='R1',measurement_type='TEMPERATURE_C',value=70,unit=unit)
    result=app.row(measured,'max_temperature','°C',logged)
    assert result['delta']==0 and result['agrees'] is True

@pytest.mark.parametrize('unit',['psi','PSI','Psi'])
def test_psi_unit_normalization(unit):
    measured=dict(value=100,confidence=.8,flags=[])
    logged=app.Logged(reading_id='R1',measurement_type='PRESSURE_PSI',value=100,unit=unit)
    assert app.row(measured,'pressure','psi',logged)['agrees'] is True
