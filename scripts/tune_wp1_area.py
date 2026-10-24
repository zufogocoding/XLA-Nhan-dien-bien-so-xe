"""Screen area gates on a fixed validation sample; never change production defaults."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

import cv2
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evaluate_wp1 import iou
from src.detection import find_candidates


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("split",type=Path,nargs="?",default=Path("Vietnam License Plate.v2i.coco/valid"))
    parser.add_argument("--limit",type=int,default=250)
    args=parser.parse_args()
    if args.split.name == "test":
        raise ValueError("tuning on the test split is prohibited")
    data=json.loads((args.split / '_annotations.coco.json').read_text(encoding='utf-8'))
    boxes=defaultdict(list)
    for ann in data['annotations']:
        x,y,w,h=ann['bbox']; boxes[ann['image_id']].append((x,y,x+w,y+h))
    indices=np.random.default_rng(2026).permutation(len(data['images']))[:args.limit]
    trials={(0.005,0.30):{'tp':0,'fp':0,'fn':0},(0.002,0.60):{'tp':0,'fp':0,'fn':0},(0.001,0.90):{'tp':0,'fp':0,'fn':0}}
    for position,index in enumerate(indices,1):
        item=data['images'][int(index)]
        image=cv2.imdecode(np.fromfile(args.split / item['file_name'],np.uint8),cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError('validation image is unreadable')
        gt=boxes[item['id']]
        for (minimum,maximum),counts in trials.items():
            candidates=find_candidates(image,max_candidates=1,min_area_fraction=minimum,max_area_fraction=maximum)
            correct=bool(candidates and max((iou(candidates[0].bbox,box) for box in gt),default=0)>=0.5)
            counts['tp']+=int(correct); counts['fp']+=len(candidates)-int(correct); counts['fn']+=len(gt)-int(correct)
        if position % 50 == 0:
            print(f'validation images screened: {position}/{len(indices)}',flush=True)
    report={'split':str(args.split),'images':len(indices),'seed':2026,'iou_threshold':0.5,'production_defaults_unchanged':True,'trials':[]}
    for (minimum,maximum),counts in trials.items():
        tp,fp,fn=counts['tp'],counts['fp'],counts['fn']; p=tp/(tp+fp) if tp+fp else 0; r=tp/(tp+fn) if tp+fn else 0
        report['trials'].append({'min_area_fraction':minimum,'max_area_fraction':maximum,**counts,'precision':p,'recall':r,'f1':2*p*r/(p+r) if p+r else 0})
    Path('reports/wp1_validation_area_screen.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
