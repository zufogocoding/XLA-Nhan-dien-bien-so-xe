"""Validation-only check of consistent plate scale and broken-stroke repair."""

from dataclasses import asdict
import json
from pathlib import Path
import sys

import cv2
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.pipeline_wp2 import SegmentationConfig,segment_plate
from scripts.evaluate_wp2_wp3 import box_iou,ground_truth_lines

items=[r for r in json.loads(Path('data/plates.json').read_text(encoding='utf-8')) if r['split']=='valid' and not r['font_chart']]
indices=np.random.default_rng(2026).permutation(len(items))[:150]
configs=[SegmentationConfig(working_height=height,broken_kernel=kernel) for height in (None,96,128,160) for kernel in (None,(3,3),(1,3))]
configs += [SegmentationConfig(working_height=128,threshold_method='adaptive',adaptive_block_size=block,broken_kernel=kernel) for block in (11,31,51) for kernel in (None,(3,3))]
trials=[{'config':config,'tp':0,'pred':0,'gt':0,'line_correct':0} for config in configs]
for position,index in enumerate(indices,1):
    item=items[int(index)]; image=cv2.imdecode(np.fromfile(item['image_path'],np.uint8),cv2.IMREAD_COLOR); gt_lines=len(ground_truth_lines(item['characters']))
    for trial in trials:
        result=segment_plate(image,trial['config']); matched=set()
        for box in result['positions']:
            overlap,i=max(((box_iou(box,char['bbox']),i) for i,char in enumerate(item['characters']) if i not in matched),default=(0,-1))
            if overlap>=.5: matched.add(i)
        trial['tp']+=len(matched);trial['pred']+=result['num_chars'];trial['gt']+=len(item['characters']);trial['line_correct']+=len(result['line_ranges'])==gt_lines
    if position%50==0:print(f'WP2 scale validation: {position}/150',flush=True)
report={'split':'valid','images':len(indices),'seed':2026,'trials':[]}
for trial in trials:
    p=trial['tp']/trial['pred'] if trial['pred'] else 0;r=trial['tp']/trial['gt']
    report['trials'].append({'config':asdict(trial['config']),'precision':p,'recall':r,'f1':2*p*r/(p+r) if p+r else 0,'line_accuracy':trial['line_correct']/len(indices)})
report['trials'].sort(key=lambda row:row['f1'],reverse=True)
Path('reports/wp2_scale_validation_tuning.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report['trials'][:5],indent=2),flush=True)
