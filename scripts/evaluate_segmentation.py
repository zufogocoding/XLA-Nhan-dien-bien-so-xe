"""Measure WP2 box/line metrics on a named prepared-data split."""

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.pipeline_wp2 import SegmentationConfig,segment_plate
from scripts.evaluate_wp2_wp3 import box_iou,ground_truth_lines


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--split',choices=('train','valid','test'),default='valid')
    parser.add_argument('--working-height',type=int,default=SegmentationConfig().working_height)
    args=parser.parse_args()
    items=[r for r in json.loads(Path('data/plates.json').read_text(encoding='utf-8')) if r['split']==args.split and not r['font_chart']]
    rows=[]
    for item in items:
        image=cv2.imdecode(np.fromfile(item['image_path'],np.uint8),cv2.IMREAD_COLOR)
        result=segment_plate(image,SegmentationConfig(working_height=args.working_height))
        matched=set()
        for box in result['positions']:
            overlap,index=max(((box_iou(box,g['bbox']),i) for i,g in enumerate(item['characters']) if i not in matched),default=(0,-1))
            if overlap>=.5: matched.add(index)
        rows.append({'name':item['source_image'],'gt':len(item['characters']),'pred':result['num_chars'],'matched':len(matched),'gt_lines':len(ground_truth_lines(item['characters'])),'pred_lines':len(result['line_ranges'])})
    total=sum(r['gt'] for r in rows); predicted=sum(r['pred'] for r in rows); correct=sum(r['matched'] for r in rows)
    report={'split':args.split,'images':len(rows),'gt_characters':total,'proposals':predicted,'matched':correct,'accuracy_at_iou_0_5':correct/total,'precision':correct/predicted if predicted else 0,'derived_line_count_accuracy':sum(r['gt_lines']==r['pred_lines'] for r in rows)/len(rows),'cases':rows}
    suffix=f'_h{args.working_height}' if args.working_height else ''
    report['working_height']=args.working_height
    Path(f'reports/wp2_{args.split}_segmentation{suffix}.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2),flush=True)
