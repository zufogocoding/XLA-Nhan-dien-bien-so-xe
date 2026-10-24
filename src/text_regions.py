"""Plate proposals from aligned dark connected components at several scales.

This complements the contour detector when a plate border joins the car body.
No OCR labels or known plate strings are used to generate these regions.
"""

import cv2
import numpy as np

from .detection import Candidate, _iou


def text_regions(image: np.ndarray) -> list[Candidate]:
    height, width = image.shape[:2]
    scale = min(1., 900 / max(height, width))
    work = cv2.resize(image, None, fx=scale, fy=scale) if scale < 1 else image
    gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    masks = [cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]]
    for block in (31, 61):
        masks.append(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,block,9))
    candidates = []
    for mask in masks:
        count, _, stats, _ = cv2.connectedComponentsWithStats(mask)
        boxes = [(int(x),int(y),int(bw),int(bh)) for x,y,bw,bh,area in stats[1:]
                 if max(7,.015*h) <= bh <= .24*h and .12 <= bw/max(1,bh) <= 1.4
                 and .12 <= area/max(1,bw*bh) <= .9]
        if len(boxes) > 600:
            continue
        remaining = set(range(len(boxes)))
        while remaining:
            seed = remaining.pop()
            group, frontier = [seed], [seed]
            while frontier:
                i = frontier.pop()
                x,y,bw,bh = boxes[i]
                neighbors = []
                for j in remaining:
                    xx,yy,ww,hh = boxes[j]
                    gap = max(x,xx)-min(x+bw,xx+ww)
                    if .65 <= bh/hh <= 1.55 and abs(y+bh/2-yy-hh/2) < .4*max(bh,hh) and -.2*min(bw,ww) <= gap <= 1.5*max(bh,hh):
                        neighbors.append(j)
                for j in neighbors:
                    remaining.remove(j);group.append(j);frontier.append(j)
            if not 5 <= len(group) <= 11:
                continue
            glyphs = [boxes[i] for i in group]
            typical = float(np.median([box[3] for box in glyphs]))
            points = np.array([(x+dx*bw,y+dy*bh) for x,y,bw,bh in glyphs for dx,dy in ((0,0),(1,0),(1,1),(0,1))],np.float32)
            rect = cv2.minAreaRect(points)
            (cx,cy),(rw,rh),angle = rect
            if rw < rh:
                rw,rh=rh,rw;angle-=90
            angle=(angle+90)%180-90
            if not 2.2 < rw/max(1,rh) < 14 or abs(angle) > 25:
                continue
            corners=cv2.boxPoints(((cx,cy),(rw+.45*typical,rh+.55*typical),angle))
            x1,y1=np.floor(corners.min(axis=0)).astype(int)
            x2,y2=np.ceil(corners.max(axis=0)).astype(int)
            box=(max(0,round(x1/scale)),max(0,round(y1/scale)),min(width,round(x2/scale)),min(height,round(y2/scale)))
            alignment=float(np.std([box[1]+box[3]/2 for box in glyphs])/typical)
            score=.5+.025*min(len(group),9)-.1*alignment
            candidates.append(Candidate(box,corners/scale,score,'aligned_components'))
    unique=[]
    for candidate in sorted(candidates,key=lambda c:c.score,reverse=True):
        if all(_iou(candidate.bbox,other.bbox)<.7 for other in unique):
            unique.append(candidate)
    return unique[:15]
