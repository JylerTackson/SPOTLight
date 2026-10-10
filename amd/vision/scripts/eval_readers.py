"""Measured CPU evaluation; no cached timings and no GPU claims."""
import argparse
import json
import platform
import socket
import sys
import time
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import VisionRequest, vision, extract
from textaxes import ocr
from readers import thermal,gauge
import base64
ROOT=Path(__file__).resolve().parents[3]

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=ROOT/'amd/vision/data/synth');p.add_argument('--out',type=Path,default=ROOT/'amd/vision/results/readers');args=p.parse_args()
    records=[]
    for item in map(json.loads,(args.data/'manifest.jsonl').read_text().splitlines()):
        request=VisionRequest(image_b64=base64.b64encode((args.data/item['image']).read_bytes()).decode(),
                    action_type='THERMAL_INSPECTION' if item['measurement_type']=='TEMPERATURE_C' else 'GAUGE_READING',
                    calibration=item['calibration'],pairing='synthetic',logged=dict(reading_id=item['reading_id'],measurement_type=item['measurement_type'],value=item['logged_value'],unit=item['unit']))
        extract.cache_clear();response=vision(request);row=response['vision'][0]
        image=cv2.imread(str(args.data/item['image']));reader=thermal if item['measurement_type']=='TEMPERATURE_C' else gauge
        result=reader.read(image,response['ocr'],item['calibration'])
        center_error=None
        if result.get('box') and item.get('hotspot_box'):
            actual=np.array(result['box'][:2])+np.array(result['box'][2:])/2
            expected=np.array(item['hotspot_box'][:2])+np.array(item['hotspot_box'][2:])/2
            center_error=float(np.linalg.norm(actual-expected))
        records.append(dict(item,row=row,latency_ms=response['latency_ms'],center_error_px=center_error))
    metrics={}
    for split in ['train','heldout']:
        metrics[split]={}
        for measurement in ['PRESSURE_PSI','TEMPERATURE_C']:
            subset=[r for r in records if r['split']==split and r['measurement_type']==measurement]
            readable=[r for r in subset if r['variant']!='unreadable' and r['row']['value'] is not None]
            errors=[abs(r['row']['value']-r['rendered_value']) for r in readable]
            twins=[r for r in subset if r['variant']!='unreadable']
            judged=[r for r in twins if r['row']['agrees'] is not None]
            bad=[r for r in subset if r['variant']=='unreadable']
            centers=[r['center_error_px'] for r in readable if r['center_error_px'] is not None]
            result=dict(count=len(subset),measurable_count=len(readable),low_confidence_rate=float(np.mean([r['row']['confidence']<.5 for r in subset])),
                        agrees_accuracy_all_twins=float(np.mean([r['row']['agrees']==(r['variant']=='true') for r in twins])),
                        agrees_coverage=len(judged)/len(twins),agrees_accuracy_decided=float(np.mean([r['row']['agrees']==(r['variant']=='true') for r in judged])) if judged else None,
                        unreadable_correctly_flagged_rate=float(np.mean([r['row']['confidence']<.5 for r in bad])) if bad else None,
                        agrees_accuracy_by_variant={v:float(np.mean([r['row']['agrees']==(v=='true') for r in twins if r['variant']==v])) for v in ['true','perturbed']},
                        latency_p50_ms=float(np.percentile([r['latency_ms'] for r in subset],50)),latency_p95_ms=float(np.percentile([r['latency_ms'] for r in subset],95)))
            if measurement=='PRESSURE_PSI':result.update(mae_percent_fs=float(np.mean(errors)/200*100) if errors else None,within_2_percent_fs=float(np.mean(np.array(errors)<=4)) if errors else None)
            else:result.update(max_temperature_mae_c=float(np.mean(errors)) if errors else None,hotspot_center_error_px=float(np.mean(centers)) if centers else None)
            metrics[split][measurement]=result
    kit={}
    for path in sorted((ROOT/'SPOTDATA/SPOT_KnightHacks_Challenge_Kit Part One/04_ASSETS/sample_inspection_images').glob('*.jpg')):
        action='THERMAL_INSPECTION' if path.name.startswith('thermal') else 'GAUGE_READING' if path.name.startswith('gauge') else 'VISUAL_INSPECTION'
        response=vision(VisionRequest(image_b64=base64.b64encode(path.read_bytes()).decode(),action_type=action))
        kit[path.name]=dict(router=response['router'],vision=response['vision'],ocr=response['ocr'],latency_ms=response['latency_ms'])
    machine=dict(host=socket.gethostname(),platform=platform.platform(),processor=platform.processor(),device='CPU',python=platform.python_version())
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'metrics.json').write_text(json.dumps(dict(machine=machine,metrics=metrics,kit_samples=kit,per_image=records),indent=2,ensure_ascii=False)+'\n')
    report='# Reader evaluation\n\nRun on CPU: '+json.dumps(machine)+'\n\n'
    report+='150 deterministic synthetic images; mission splits from System 1 manifest. These are synthetic checks, not real-world accuracy.\n'
    report+='Null measurements are excluded from numerical MAE; measurable counts, low-confidence rate and abstentions are reported separately. Agreement accuracy over all twins counts abstentions as failures; decided accuracy includes only non-null decisions. Latencies include OCR and annotation, cache cleared before every render.\n\n'
    for split,results in metrics.items():
        report+='## '+split+'\n\n```json\n'+json.dumps(results,indent=2)+'\n```\n\n'
    report+='## Kit samples (eval/demo only)\n\n'
    for name,result in kit.items():report+='- '+name+': '+json.dumps(dict(router=result['router'],vision=result['vision']),ensure_ascii=False)+'\n'
    report+='\nAcoustic and visual scenes return unsupported modality: their readers are out of scope. VLM calls are reserved and unused. OCR inference is offline using bundled RapidOCR models. Real-world accuracy remains unverified.\n'
    (args.out/'report.md').write_text(report)
    print(json.dumps(metrics,indent=2))
if __name__=='__main__':main()
