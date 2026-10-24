"""Compare WP2 geometry options on a fixed validation sample only."""

from dataclasses import asdict
from itertools import product
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
trials=[{'config':SegmentationConfig(threshold_method=method,min_aspect=ratio,clean_long_borders=clean),'tp':0,'pred':0,'gt':0,'line_correct':0} for method,ratio,clean in product(('otsu','adaptive'),(.2,.12,.08),(False,True))]
for position,index in enumerate(indices,1):
    item=items[int(index)]
    image=cv2.imdecode(np.fromfile(item['image_path'],np.uint8),cv2.IMREAD_COLOR)
    gt_lines=len(ground_truth_lines(item['characters']))
    for trial in trials:
        result=segment_plate(image,trial['config'])
        matched=set()
        for box in result['positions']:
            overlap,i=max(((box_iou(box,char['bbox']),i) for i,char in enumerate(item['characters']) if i not in matched),default=(0,-1))
            if overlap>=.5: matched.add(i)
        trial['tp']+=len(matched); trial['pred']+=result['num_chars']; trial['gt']+=len(item['characters']); trial['line_correct']+=len(result['line_ranges'])==gt_lines
    if position % 50 == 0: print(f'WP2 valid sample: {position}/150',flush=True)
report={'split':'valid','images':len(indices),'seed':2026,'trials':[]}
for trial in trials:
    p=trial['tp']/trial['pred'] if trial['pred'] else 0; r=trial['tp']/trial['gt']
    report['trials'].append({'config':asdict(trial['config']),'matched':trial['tp'],'gt':trial['gt'],'proposals':trial['pred'],'precision':p,'recall':r,'f1':2*p*r/(p+r) if p+r else 0,'line_accuracy':trial['line_correct']/len(indices)})
report['trials'].sort(key=lambda item:item['f1'],reverse=True)
Path('reports/wp2_validation_tuning.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
