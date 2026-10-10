"""Deterministic reading-derived images; kit photos are never copied."""
import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

ROOT=Path(__file__).resolve().parents[3]
KIT=ROOT/'SPOTDATA/SPOT_KnightHacks_Challenge_Kit Part One'
VERSION='synth-1.0'
IRON=LinearSegmentedColormap.from_list('ironbow',['#090020','#500080','#b02055','#ee6820','#ffdf30','#ffffdd'])

def render(reading_id, variant, measurement_type, value):
    seed=int(hashlib.sha1((reading_id+variant).encode()).hexdigest()[:8],16)
    rng=np.random.default_rng(seed)
    thermal=measurement_type=='TEMPERATURE_C'
    rotation=float(rng.uniform(-8,8))
    calibration=dict(unit='°C' if thermal else 'psi',min_value=25 if thermal else 0,
                     max_value=100 if thermal else 200,theta_min_deg=135+rotation,theta_max_deg=405+rotation)
    box=None
    if thermal:
        h,w=180,200; yy,xx=np.mgrid[:h,:w]; cx=int(rng.integers(60,135));cy=int(rng.integers(55,125))
        ambient=float(rng.uniform(30, min(38,value-1))) if value>31 else 25
        field=ambient+(value-ambient)*np.exp(-((xx-cx)**2+(yy-cy)**2)/(2*17**2))
        rgb=(IRON(np.clip((field-25)/75,0,1))[:,:,:3]*255).astype(np.uint8)
        image=Image.new('RGB',(260,200),'white');image.paste(Image.fromarray(rgb),(0,10))
        draw=ImageDraw.Draw(image)
        bar=(IRON(np.linspace(1,0,160))[:,:3]*255).astype(np.uint8)
        image.paste(Image.fromarray(np.repeat(bar[:,None,:],12,axis=1)),(210,20))
        for temperature in [100,75,50,25]:
            y=20+(100-temperature)/75*159
            draw.text((225,y-5),str(temperature),fill='black')
        # Thermal scene is rotated, leaving its calibration bar vertical.
        scene=image.crop((0,10,200,190)).rotate(rotation,resample=Image.Resampling.BICUBIC)
        image.paste(scene,(0,10))
        radians=np.deg2rad(rotation);dx=cx-100;dy=cy-90
        tx=100+dx*np.cos(radians)+dy*np.sin(radians);ty=100-dx*np.sin(radians)+dy*np.cos(radians)
        box=[float(tx-17),float(ty-17),34,34]
    else:
        fig,ax=plt.subplots(figsize=(2.4,2.4),dpi=100)
        ax.set(xlim=(-1.2,1.2),ylim=(-1.2,1.2));ax.set_aspect('equal');ax.axis('off')
        ax.add_patch(plt.Circle((0,0),1,fill=False,color='black',lw=2))
        for tick in range(0,201,25):
            theta=np.deg2rad(135+tick/200*270)
            ax.plot([.82*np.cos(theta),.96*np.cos(theta)],[-.82*np.sin(theta),-.96*np.sin(theta)],color='black',lw=1)
            ax.text(.70*np.cos(theta),-.70*np.sin(theta),str(tick),ha='center',va='center',fontsize=8)
        theta=np.deg2rad(135+value/200*270)
        ax.plot([0,.68*np.cos(theta)],[0,-.68*np.sin(theta)],color='black',lw=3)
        ax.add_patch(plt.Circle((0,0),.045,color='black'))
        ax.text(0,-.35,'psi',ha='center',fontsize=8)
        fig.subplots_adjust(0,0,1,1);stream=io.BytesIO();fig.savefig(stream,format='png');plt.close(fig)
        image=Image.open(stream).convert('RGB').rotate(-rotation,resample=Image.Resampling.BICUBIC,fillcolor='white')
    if variant=='unreadable':
        ImageDraw.Draw(image).rectangle((0,0,image.width,image.height),fill=(245,245,245))
    else:
        if rng.random()<.35:
            overlay=Image.new('RGBA',image.size);d=ImageDraw.Draw(overlay)
            d.ellipse((5,8,55,35),fill=(255,255,255,75));image=Image.alpha_composite(image.convert('RGBA'),overlay).convert('RGB')
        image=image.filter(ImageFilter.GaussianBlur(float(rng.uniform(0,.65))))
    output=io.BytesIO();image.save(output,format='JPEG',quality=int(rng.integers(40,91)))
    return output.getvalue(),seed,calibration,box

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'amd/vision/data/synth')
    parser.add_argument('--with-vision-rows',action='store_true');parser.add_argument('--service-url',default='http://127.0.0.1:8084')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    heldout=set(json.loads((ROOT/'amd/system1/data/manifest.json').read_text())['holdout_missions'])
    rows=[r for r in csv.DictReader((KIT/'02_DATA/readings.csv').open()) if r['measurement_type'] in ['TEMPERATURE_C','PRESSURE_PSI']]
    manifest=[]
    for i,row in enumerate(rows):
        for variant in ['true','perturbed']+(['unreadable'] if i<10 else []):
            logged=float(row['value']);value=logged
            if variant=='perturbed':
                rng=np.random.default_rng(int(hashlib.sha1((row['reading_id']+variant).encode()).hexdigest()[:8],16))
                fs=75 if row['measurement_type']=='TEMPERATURE_C' else 200
                low=25 if fs==75 else 0;high=100 if fs==75 else 200
                shift=float(rng.uniform(.15,.4)*fs);value=logged+shift if logged<(low+high)/2 else logged-shift
                value=float(np.clip(value,low,high))
            data,seed,cal,box=render(row['reading_id'],variant,row['measurement_type'],value)
            name=f"{row['reading_id']}-{variant}.jpg";(args.out/name).write_bytes(data)
            record=dict(image=name,reading_id=row['reading_id'],mission_id=row['mission_id'],split='heldout' if row['mission_id'] in heldout else 'train',
                        measurement_type=row['measurement_type'],unit=row['unit'],logged_value=logged,rendered_value=value,variant=variant,
                        calibration=cal,seed=seed,renderer_version=VERSION)
            if box:record['hotspot_box']=box
            manifest.append(record)
            if args.with_vision_rows:
                payload=dict(image_b64=base64.b64encode(data).decode(),action_type='THERMAL_INSPECTION' if row['measurement_type']=='TEMPERATURE_C' else 'GAUGE_READING',
                             calibration=cal,pairing='synthetic',logged=dict(reading_id=row['reading_id'],measurement_type=row['measurement_type'],value=logged,unit=row['unit']))
                request=urllib.request.Request(args.service_url+'/v1/vision',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(request,timeout=60) as response: result=json.load(response)
                (args.out/(name+'.vision.json')).write_text(json.dumps(result,ensure_ascii=False))
    (args.out/'manifest.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in manifest))
    print(f'Rendered {len(manifest)} images in {args.out}')
if __name__=='__main__':main()
