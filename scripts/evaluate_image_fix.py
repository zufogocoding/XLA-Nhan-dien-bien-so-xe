"""Compare image-processing revisions on labeled crops without changing splits."""

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.character_classifier import CharacterClassifier
from src.pipeline_wp2 import segment_plate
from src.pipeline_wp3 import recognize_characters
from scripts.evaluate_wp2_wp3 import box_iou, edit_distance, ground_truth_lines


def evaluate(split, output, limit=None, reader=False):
    manifest = json.loads(Path('models/ocr_manifest.json').read_text(encoding='utf-8'))
    classifier = CharacterClassifier(Path('models') / manifest['artifact'])
    items = [r for r in json.loads(Path('data/plates.json').read_text(encoding='utf-8')) if r['split'] == split and not r['font_chart']]
    if limit:
        items = sorted(items, key=lambda r:r['group_id'])[:limit]
    cases = []
    for item in items:
        image = cv2.imdecode(np.fromfile(item['image_path'], np.uint8), cv2.IMREAD_COLOR)
        start = perf_counter()
        if reader:
            from src.plate_reader import rank_plate_candidates
            hypotheses=rank_plate_candidates(image,classifier)
            result=hypotheses[0]
            prediction=result['ocr']['raw_text']
        else:
            result = segment_plate(image)
            prediction = recognize_characters(result['characters'], classifier)['raw_text']
        elapsed = (perf_counter() - start)*1000
        lines = ground_truth_lines(item['characters'])
        expected = ''.join(c['char'] for line in lines for c in line)
        matched = set()
        for box in result['positions']:
            overlap, index = max(((box_iou(box, g['bbox']), i) for i,g in enumerate(item['characters']) if i not in matched), default=(0,-1))
            if overlap >= .5:
                matched.add(index)
        case={'image':item['source_image'],'expected':expected,'predicted':prediction,'matched':len(matched),'gt':len(item['characters']),'proposals':result['num_chars'],'correct_lines':len(lines)==len(result['line_ranges']),'edits':edit_distance(expected,prediction),'ms':elapsed}
        if reader:
            case['candidates']=[{'predicted':r['ocr']['raw_text'],'n':r['num_chars'],'height_cv':r['height_cv'],'edge':r['edge_fragments'],'mean_logp':float(np.mean(np.log(np.clip(r['ocr']['confidences'],1e-6,1)))) if r['num_chars'] else -10,'method':r['threshold_method'],'clean':r['frame_cleanup']} for r in hypotheses]
        cases.append(case)
    total = sum(r['gt'] for r in cases)
    matched = sum(r['matched'] for r in cases)
    proposals = sum(r['proposals'] for r in cases)
    report = {'split':split,'images':len(cases),'segmentation_recall':matched/total,'segmentation_precision':matched/proposals if proposals else 0,'line_count_accuracy':np.mean([r['correct_lines'] for r in cases]),'sequence_accuracy':np.mean([r['expected']==r['predicted'] for r in cases]),'cer':sum(r['edits'] for r in cases)/total,'mean_ms':np.mean([r['ms'] for r in cases]),'model':manifest['artifact'],'scope':'WP2 + unchanged HOG/SVM on annotated source plate crops, not full scenes','cases':cases}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--split',choices=('train','valid','test'),default='valid')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--limit',type=int)
    parser.add_argument('--reader',action='store_true')
    args = parser.parse_args()
    evaluate(args.split,args.output,args.limit,args.reader)
