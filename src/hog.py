"""Histogram of Oriented Gradients (HOG) feature extractor.

Implemented in pure NumPy because this OpenCV build has no cv2.HOGDescriptor.
Standard Dalal-Triggs style: 8x8 cells, 16x16 blocks, 50% overlap, 9 bins,
L2-Hys block normalization.
"""
import cv2
import numpy as np

WIN_W, WIN_H = 64, 32
CELL = 8
BLOCK = 16
STRIDE = 8
NBINS = 9


def _gradients(gray: np.ndarray):
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=1)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=1)
    mag = np.hypot(gx, gy)
    ang = np.degrees(np.arctan2(gy, gx)) % 180.0
    return mag, ang


def hog_features(image: np.ndarray) -> np.ndarray:
    """Return a 1-D HOG descriptor for a BGR/gray image (any size)."""
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    gray = cv2.resize(gray, (WIN_W, WIN_H), interpolation=cv2.INTER_AREA).astype(np.float32)
    mag, ang = _gradients(gray)

    ncells_x = WIN_W // CELL  # 8
    ncells_y = WIN_H // CELL  # 4
    # cell histograms
    hist = np.zeros((ncells_y, ncells_x, NBINS), dtype=np.float32)
    bin_width = 180.0 / NBINS
    for cy in range(ncells_y):
        for cx in range(ncells_x):
            m = mag[cy * CELL:(cy + 1) * CELL, cx * CELL:(cx + 1) * CELL]
            a = ang[cy * CELL:(cy + 1) * CELL, cx * CELL:(cx + 1) * CELL]
            # soft binning
            for i in range(CELL):
                for j in range(CELL):
                    b = int(a[i, j] / bin_width) % NBINS
                    hist[cy, cx, b] += m[i, j]
                    # interpolate to next bin
                    frac = (a[i, j] / bin_width) - b
                    nb = (b + 1) % NBINS
                    hist[cy, cx, nb] += m[i, j] * frac
                    hist[cy, cx, b] -= m[i, j] * frac  # keep sum = mag (approx)

    # blocks
    nblocks_x = (WIN_W - BLOCK) // STRIDE + 1  # 7
    nblocks_y = (WIN_H - BLOCK) // STRIDE + 1  # 3
    feat = []
    for by in range(nblocks_y):
        for bx in range(nblocks_x):
            block = hist[by * (STRIDE // CELL):(by * (STRIDE // CELL) + BLOCK // CELL),
                        bx * (STRIDE // CELL):(bx * (STRIDE // CELL) + BLOCK // CELL), :].ravel().copy()
            # L2-Hys
            nrm = np.linalg.norm(block) + 1e-6
            block = block / nrm
            block = np.clip(block, 0, 0.2)
            nrm2 = np.linalg.norm(block) + 1e-6
            block = block / nrm2
            feat.append(block)
    return np.concatenate(feat).astype(np.float32)


def crop_features(image: np.ndarray) -> np.ndarray:
    """Compact 7-dim heuristic feature vector from a BGR crop."""
    if image.ndim == 2:
        bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        bgr = image
    h, w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    edges = cv2.Canny(gray, 80, 180)
    edge_density = cv2.countNonZero(edges) / max(1, edges.size)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    # color coverage: max over plate-color masks
    masks = []
    for (lo, hi) in [((0, 0, 155), (179, 85, 255)), ((15, 70, 100), (40, 255, 255)),
                     ((90, 45, 45), (135, 255, 255)), ((0, 80, 70), (10, 255, 255))]:
        masks.append(cv2.inRange(hsv, np.array(lo), np.array(hi)))
    color_cov = max(cv2.countNonZero(m) / max(1, m.size) for m in masks)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    fg = cv2.countNonZero(th)
    char_density = min(fg, th.size - fg) / max(1, th.size)
    minority = th if fg <= th.size // 2 else cv2.bitwise_not(th)
    nlab, _ = cv2.connectedComponents(minority)
    nlab -= 1
    # rect_area (solidity) of largest contour in edge map
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        c = max(contours, key=cv2.contourArea)
        x, y, bw, bh = cv2.boundingRect(c)
        rect_area = cv2.contourArea(c) / max(1, bw * bh)
    else:
        rect_area = 0.0
    ratio = w / max(1, h)
    return np.array([ratio, rect_area, edge_density, color_cov,
                     char_density, min(nlab, 50) / 50.0], dtype=np.float32)
