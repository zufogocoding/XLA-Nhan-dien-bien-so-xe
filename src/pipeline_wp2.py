"""WP2 public interface: plate image -> ordered normalized characters."""

from dataclasses import dataclass, replace

import cv2
import numpy as np

from .binarization import binarize
from .character_filter import filter_characters
from .character_segmentation import remove_plate_frame, remove_long_border_strokes, clean_frame_strokes, merge_vertical_fragments, segment_characters
from .fix_broken import fix_broken
from .fix_touching import split_touching
from .line_separation import separate_lines, group_component_lines
from .normalize_character import normalize_character

SEGMENTATION_VERSION = "wp2-0.4-multithreshold-frame-aware"

@dataclass(frozen=True)
class SegmentationConfig:
    character_size: int = 32
    threshold_method: str = "auto"
    segmentation_method: str = "components"
    broken_kernel: tuple[int, int] | None = None
    min_aspect: float = 0.2
    max_aspect: float = 1.0
    clean_long_borders: bool = False
    working_height: int | None = 128
    adaptive_block_size: int = 11
    frame_cleanup: bool = False
    merge_fragments: bool = False


def _segment_binary(binary: np.ndarray, config: SegmentationConfig) -> dict:
    if config.frame_cleanup:
        binary = clean_frame_strokes(binary)
    if config.clean_long_borders:
        binary = remove_long_border_strokes(binary)
    binary = remove_plate_frame(binary)
    if config.broken_kernel is not None:
        binary = fix_broken(binary, kernel_size=config.broken_kernel)
    component_boxes=[]
    for x,y,width,height in segment_characters(binary,config.segmentation_method):
        if width > .7*binary.shape[1] and height > .7*binary.shape[0]:
            continue
        for dx,dy,w,h in split_touching(binary[y:y+height,x:x+width]):
            component_boxes.append((x+dx,y+dy,w,h))
    grouped=group_component_lines(component_boxes,binary.shape[0])
    if grouped:
        lines=[(min(box[1] for box in group if box[3]>=binary.shape[0]*0.18),max(box[1]+box[3] for box in group if box[3]>=binary.shape[0]*0.18)) for group in grouped]
    else:
        lines = separate_lines(binary)
    characters, positions, line_ids = [], [], []
    for line_id, (start, end) in enumerate(lines):
        line = binary[start:end]
        proposals = []
        if grouped:
            proposals=[(x,y-start,w,h) for x,y,w,h in grouped[line_id]]
        else:
            for x, y, width, height in segment_characters(line, config.segmentation_method):
                for dx, dy, w, h in split_touching(line[y:y + height, x:x + width]):
                    proposals.append((x + dx, y + dy, w, h))
        if config.merge_fragments:
            proposals=merge_vertical_fragments(proposals,line.shape[0])
        boxes = filter_characters(proposals, line.shape, min_aspect=config.min_aspect, max_aspect=config.max_aspect)
        for x, y, width, height in sorted(boxes, key=lambda b: b[0]):
            characters.append(normalize_character(line[y:y + height, x:x + width], config.character_size))
            positions.append((x, start + y, width, height))
            line_ids.append(line_id)
    return {
        "characters": characters, "positions": positions,
        "line_type": f"{len(lines)}_line" if lines else None,
        "num_chars": len(characters), "line_ids": line_ids,
        "line_ranges": lines, "binary": binary,
        "line_method": "component_centers" if grouped else "projection",
    }


def segment_plate_candidates(plate_image: np.ndarray, config: SegmentationConfig | None = None) -> list[dict]:
    """Read top-to-bottom/left-to-right; positions refer to input plate pixels.

    Compare both foreground polarities geometrically. Dark surrounding pixels
    can outnumber plate background pixels even for dark text on a light plate;
    selecting the minority class alone then erases the characters.
    Empty foreground yields no characters and line_type=None. No characters
    are invented to fit a count. Accuracy requires external labels.
    """
    config = config or SegmentationConfig()
    if config.character_size not in (28, 32):
        raise ValueError("character_size must be 28 or 32")
    if not isinstance(plate_image,np.ndarray) or plate_image.dtype != np.uint8 or plate_image.ndim not in (2,3) or min(plate_image.shape[:2]) == 0:
        raise ValueError("expected a nonempty uint8 BGR/grayscale plate")
    original_height,original_width=plate_image.shape[:2]
    if original_width/original_height > 5.5:
        # Foreshortened car plates can have glyphs wider than their height.
        config=replace(config,max_aspect=max(config.max_aspect,1.35))
    work=plate_image
    scale=1.0
    if config.working_height is not None:
        if not 32 <= config.working_height <= 512:
            raise ValueError("working_height must be 32..512 or None")
        scale=config.working_height/original_height
        work=cv2.resize(plate_image,(max(1,round(original_width*scale)),config.working_height),interpolation=cv2.INTER_AREA if scale<1 else cv2.INTER_CUBIC)
    if config.threshold_method == 'auto':
        gray = cv2.cvtColor(work,cv2.COLOR_BGR2GRAY) if work.ndim==3 else work
        contrast = cv2.createCLAHE(clipLimit=2.,tileGridSize=(4,4)).apply(gray)
        masks = [('otsu_dark',binarize(gray,'otsu',invert=True)),
                 ('otsu_light',binarize(gray,'otsu',invert=False)),
                 ('clahe_otsu',binarize(contrast,'otsu',invert=True)),
                 ('adaptive_31',binarize(gray,'adaptive',invert=True,block_size=31,c=9)),
                 ('adaptive_51',binarize(gray,'adaptive',invert=True,block_size=51,c=5))]
        if original_height > 160 and scale < 1:
            detail=cv2.resize(plate_image,(work.shape[1],work.shape[0]),interpolation=cv2.INTER_CUBIC)
            masks += [('detail_31',binarize(detail,'adaptive',invert=True,block_size=31,c=9)),
                      ('detail_51',binarize(detail,'adaptive',invert=True,block_size=51,c=5))]
    else:
        base = binarize(work, config.threshold_method, invert=False,block_size=config.adaptive_block_size)
        masks = [('light',base),('dark',cv2.bitwise_not(base))]
    hypotheses = []
    for method,mask in masks:
        for cleanup in ((False,True) if config.threshold_method=='auto' else (config.frame_cleanup,)):
            merge=(method=='adaptive_31' and cleanup)
            result = _segment_binary(mask, replace(config,frame_cleanup=cleanup,merge_fragments=merge or config.merge_fragments))
            count = result['num_chars']
            heights = [b[3] for b in result['positions']]
            height_cv = float(np.std(heights)/max(1,np.mean(heights))) if heights else 1.
            edge_fragments=sum((x<=1 or x+w>=work.shape[1]-1) and w/h<.4 for x,y,w,h in result['positions'])
            result['height_cv']=height_cv
            result['edge_fragments']=int(edge_fragments)
            result['segmentation_score']=float(min(count,9)-1.5*max(0,count-9)-2*height_cv-2*edge_fragments)
            result['threshold_method']=method
            result['frame_cleanup']=cleanup
            result['merge_fragments']=merge or config.merge_fragments
            result['foreground_inverted']=method not in ('light','otsu_light')
            result['working_scale']=scale
            result['algorithm_version']=SEGMENTATION_VERSION
            if scale != 1:
                positions=[]
                for x,y,width,height in result['positions']:
                    x1,y1=max(0,round(x/scale)),max(0,round(y/scale))
                    x2,y2=min(original_width,round((x+width)/scale)),min(original_height,round((y+height)/scale))
                    positions.append((x1,y1,max(1,x2-x1),max(1,y2-y1)))
                result['positions']=positions
                result['line_ranges']=[(round(start/scale),min(original_height,round(end/scale))) for start,end in result['line_ranges']]
                result['binary']=cv2.resize(result['binary'],(original_width,original_height),interpolation=cv2.INTER_NEAREST)
            hypotheses.append(result)
    return hypotheses


def segment_plate(plate_image: np.ndarray, config: SegmentationConfig | None = None) -> dict:
    """Choose a geometric hypothesis; OCR can compare candidates separately."""
    hypotheses=segment_plate_candidates(plate_image,config)
    chosen=max(hypotheses,key=lambda result:result['segmentation_score'])
    chosen['polarity_hypotheses']=[{'inverted':r['foreground_inverted'],'num_chars':r['num_chars'],'score':r['segmentation_score']} for r in hypotheses]
    return chosen
