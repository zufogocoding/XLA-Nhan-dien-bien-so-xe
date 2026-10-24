"""Character box proposals from a white-foreground binary line."""

import cv2
import numpy as np

from .binarization import validate_binary
from .line_separation import _runs


def segment_characters(binary: np.ndarray, method: str = "components") -> list[tuple[int, int, int, int]]:
    validate_binary(binary)
    if method == "components":
        count, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        boxes = [tuple(int(v) for v in stats[i, :4]) for i in range(1, count)]
    elif method == "contours":
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = [cv2.boundingRect(contour) for contour in contours]
    elif method == "projection":
        boxes = []
        for start, end in _runs(np.any(binary, axis=0)):
            rows = np.flatnonzero(np.any(binary[:, start:end], axis=1))
            boxes.append((start, int(rows[0]), end - start, int(rows[-1] - rows[0] + 1)))
    else:
        raise ValueError("method must be 'components', 'contours' or 'projection'")
    return sorted(boxes, key=lambda box: (box[0], box[1]))


def remove_plate_frame(binary: np.ndarray) -> np.ndarray:
    """Remove border-sized components before projection, keeping internal glyphs."""
    validate_binary(binary)
    result = binary.copy()
    height, width = binary.shape
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    for i in range(1, count):
        x, y, w, h, _ = stats[i]
        frame = w >= 0.85 * width and h >= 0.85 * height
        horizontal = w >= 0.75 * width and h <= 0.12 * height and (y <= 2 or y + h >= height - 2)
        vertical = h >= 0.75 * height and w <= 0.08 * width and (x <= 2 or x + w >= width - 2)
        if frame or horizontal or vertical:
            result[labels == i] = 0
    return result


def remove_long_border_strokes(binary: np.ndarray) -> np.ndarray:
    """Disconnect long horizontal borders and vertical strokes near side edges."""
    validate_binary(binary)
    height, width = binary.shape
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((1,max(3,round(width * 0.25))),np.uint8))
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((max(3,round(height * 0.60)),1),np.uint8))
    edge_only = np.zeros_like(binary)
    margin = max(1,round(width * 0.06))
    edge_only[:,:margin] = vertical[:,:margin]
    edge_only[:,-margin:] = vertical[:,-margin:]
    return cv2.bitwise_and(binary,cv2.bitwise_not(cv2.bitwise_or(horizontal,edge_only)))


def clean_frame_strokes(binary: np.ndarray) -> np.ndarray:
    """Erase long frame strokes near image edges, retaining attached glyphs.

    Removing an entire connected frame also removes characters touching it.
    Directional opening isolates the frame strokes before component labeling.
    """
    validate_binary(binary)
    h,w=binary.shape
    horizontal=cv2.morphologyEx(binary,cv2.MORPH_OPEN,np.ones((1,max(9,round(w*.4))),np.uint8))
    vertical=cv2.morphologyEx(binary,cv2.MORPH_OPEN,np.ones((max(9,round(h*.65)),1),np.uint8))
    strokes=np.zeros_like(binary)
    my,mx=max(1,round(h*.18)),max(1,round(w*.09))
    strokes[:my]=horizontal[:my];strokes[-my:]=horizontal[-my:]
    strokes[:,:mx]=cv2.bitwise_or(strokes[:,:mx],vertical[:,:mx])
    strokes[:,-mx:]=cv2.bitwise_or(strokes[:,-mx:],vertical[:,-mx:])
    strokes=cv2.dilate(strokes,np.ones((3,3),np.uint8))
    result=cv2.bitwise_and(binary,cv2.bitwise_not(strokes))
    return result


def _merge_vertical_fragments_scalar(boxes: list[tuple[int,int,int,int]], line_height: int) -> list[tuple[int,int,int,int]]:
    """Reconnect vertically broken glyph boxes only after separating text rows."""
    result=list(boxes)
    changed=True
    while changed:
        changed=False
        for i,a in enumerate(result):
            if changed:
                break
            for j in range(i+1,len(result)):
                b=result[j]
                overlap=min(a[0]+a[2],b[0]+b[2])-max(a[0],b[0])
                gap=max(a[1],b[1])-min(a[1]+a[3],b[1]+b[3])
                x,y=min(a[0],b[0]),min(a[1],b[1])
                w,h=max(a[0]+a[2],b[0]+b[2])-x,max(a[1]+a[3],b[1]+b[3])-y
                if overlap>=.45*min(a[2],b[2]) and 0<=gap<=.2*line_height and h<=line_height and w/h<1.2:
                    result[i]=(x,y,w,h);result.pop(j);changed=True;break
    return result


def merge_vertical_fragments(boxes: list[tuple[int,int,int,int]], line_height: int) -> list[tuple[int,int,int,int]]:
    """Preserve greedy merge order while screening dense noise in NumPy.

    Photos can produce hundreds of tiny components. Python pair-by-pair scans
    dominated application runtime. Vectorized comparisons retain the same
    first compatible (i,j) pair and integer union as the scalar implementation.
    """
    result = list(boxes)
    while len(result) >= 32:
        array = np.asarray(result, dtype=np.int64)
        for i, (ax, ay, aw, ah) in enumerate(array[:-1]):
            other = array[i + 1:]
            bx, by, bw, bh = other.T
            overlap = np.minimum(ax + aw, bx + bw) - np.maximum(ax, bx)
            gap = np.maximum(ay, by) - np.minimum(ay + ah, by + bh)
            width = np.maximum(ax + aw, bx + bw) - np.minimum(ax, bx)
            height = np.maximum(ay + ah, by + bh) - np.minimum(ay, by)
            matches = np.flatnonzero(
                (overlap >= .45 * np.minimum(aw, bw)) & (gap >= 0)
                & (gap <= .2 * line_height) & (height <= line_height)
                & (width / np.maximum(height, 1) < 1.2)
            )
            if matches.size:
                j = i + 1 + int(matches[0])
                b = result[j]
                x, y = min(int(ax), b[0]), min(int(ay), b[1])
                result[i] = (x, y, max(int(ax + aw), b[0] + b[2]) - x,
                             max(int(ay + ah), b[1] + b[3]) - y)
                result.pop(j)
                break
        else:
            return result
    return _merge_vertical_fragments_scalar(result, line_height)
