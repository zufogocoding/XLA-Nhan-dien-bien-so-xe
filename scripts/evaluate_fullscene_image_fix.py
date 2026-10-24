"""Evaluate the actual CV + HOG/SVM candidate selector against plate boxes."""

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from time import perf_counter

import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.character_classifier import CharacterClassifier
from src.detection import _iou
from src.recognition_selection import select_plate_for_recognition


if __name__=='__main__':
    split=ROOT/'Vietnam License Plate.v2i.coco/test'
    data=json.loads((split/'_annotations.coco.json').read_text(encoding='utf-8'))
    ground=defaultdict(list)
    for annotation in data['annotations']:
        x,y,w,h=annotation['bbox']
        ground[annotation['image_id']].append((x,y,x+w,y+h))
    manifest=json.loads((ROOT/'models/ocr_manifest.json').read_text(encoding='utf-8'))
    classifier=CharacterClassifier(ROOT/'models'/manifest['artifact'])
    classifier.load()
    cases=[];tp=fp=fn=0
    for index,item in enumerate(data['images']):
        start=perf_counter()
        image=cv2.imdecode(np.fromfile(split/item['file_name'],np.uint8),cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(item['file_name'])
        result=select_plate_for_recognition(image,classifier)
        elapsed=(perf_counter()-start)*1000
        overlap=max((_iou(result['bbox'],box) for box in ground[item['id']]),default=0) if result else 0
        matched=int(overlap>=.5)
        tp+=matched;fp+=int(result is not None)-matched;fn+=len(ground[item['id']])-matched
        cases.append({'file':item['file_name'],'bbox':result['bbox'] if result else None,'best_iou':overlap,'source':result.get('source') if result else None,'raw_text':result['ocr']['raw_text'] if result and result.get('ocr') else None,'ms':elapsed})
        if (index+1)%25==0:
            print(f'{index+1}/{len(data["images"])} images',flush=True)
    precision=tp/(tp+fp) if tp+fp else 0;recall=tp/(tp+fn)
    report={'images':len(cases),'gt_boxes':sum(map(len,ground.values())),'tp':tp,'fp':fp,'fn':fn,'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision+recall else 0,'mean_ms':float(np.mean([r['ms'] for r in cases])),'p95_ms':float(np.percentile([r['ms'] for r in cases],95)),'sources':dict(Counter(r['source'] for r in cases)),'model':manifest['artifact'],'scope':'actual image candidate selection: OpenCV geometry and unchanged HOG/SVM; full-scene box accuracy at IoU .5, NOT full-scene OCR accuracy; latency excludes HTTP/upload and SQLite; other background work may affect timing','cases':cases}
    (ROOT/'reports/image_processing_fullscene.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2),flush=True)
