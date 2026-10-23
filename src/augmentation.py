"""Data augmentation for plate images and character patches (WP2/WP3)."""

import cv2
import numpy as np


def rotate(image: np.ndarray, angle: float) -> np.ndarray:
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    return cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )


def perspective(image: np.ndarray, amount: float, rng: np.random.Generator) -> np.ndarray:
    """Warp corners by up to ``amount`` of the image size (0.1-0.3 = strong)."""
    height, width = image.shape[:2]
    amount = float(np.clip(amount, 0.0, 0.45))
    source = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    jitter = rng.uniform(-amount, amount, size=(4, 2)).astype(np.float32)
    destination = source + jitter * np.array([width, height], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(source, destination)
    return cv2.warpPerspective(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )


def gaussian_blur(image: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return image
    return cv2.GaussianBlur(image, (0, 0), sigmaX=sigma, sigmaY=sigma)


def motion_blur(image: np.ndarray, kernel_size: int, angle: float) -> np.ndarray:
    size = max(3, kernel_size | 1)
    kernel = np.zeros((size, size), dtype=np.float32)
    kernel[size // 2, :] = 1.0
    rotation = cv2.getRotationMatrix2D((size / 2 - 0.5, size / 2 - 0.5), angle, 1.0)
    kernel = cv2.warpAffine(kernel, rotation, (size, size))
    kernel /= max(1e-6, kernel.sum())
    return cv2.filter2D(image, -1, kernel)


def brightness_contrast(
    image: np.ndarray, brightness: float = 0.0, contrast: float = 1.0
) -> np.ndarray:
    """Apply ``image * contrast + brightness`` where brightness is 0-255 units."""
    result = image.astype(np.float32) * contrast + brightness
    return np.clip(result, 0, 255).astype(np.uint8)


def add_noise(image: np.ndarray, sigma: float, rng: np.random.Generator) -> np.ndarray:
    if sigma <= 0:
        return image
    noise = rng.normal(0, sigma, image.shape).astype(np.float32)
    return np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def augment_plate(
    image: np.ndarray,
    rng: np.random.Generator | None = None,
    rotation: tuple[float, float] | float | None = None,
    perspective_amount: tuple[float, float] | float | None = None,
    blur: bool = True,
    brightness: float = 0.30,
    noise_sigma: float = 0.0,
) -> np.ndarray:
    """Random augmentation pipeline used to stress-test segmentation.

    ``rotation`` defaults to +/-15 degrees and ``perspective_amount`` to
    0.01-0.08 for already rectified plates. Pass ``perspective_amount=0.30``
    to reproduce the strong 0.1-0.3 range from the brief.
    """
    if image is None or image.size == 0:
        raise ValueError("image is empty")
    rng = rng or np.random.default_rng()

    if rotation is None:
        angle = float(rng.uniform(-15, 15))
    elif isinstance(rotation, tuple):
        angle = float(rng.uniform(*rotation))
    else:
        angle = float(rotation)
    if angle:
        image = rotate(image, angle)

    if perspective_amount is None:
        low, high = 0.01, 0.08
    elif isinstance(perspective_amount, tuple):
        low, high = perspective_amount
    else:
        low = high = float(perspective_amount)
    amount = float(rng.uniform(low, high)) if high > 0 else 0.0
    if amount > 0:
        image = perspective(image, amount, rng)

    if blur:
        if rng.random() < 0.5:
            image = gaussian_blur(image, float(rng.uniform(0.0, 1.8)))
        else:
            image = motion_blur(
                image, int(rng.integers(3, 10)), float(rng.uniform(0, 180))
            )

    if brightness > 0:
        contrast = float(rng.uniform(1.0 - brightness, 1.0 + brightness))
        offset = float(rng.uniform(-brightness, brightness) * 40)
        image = brightness_contrast(image, offset, contrast)
    if noise_sigma > 0:
        image = add_noise(image, noise_sigma, rng)
    return image


def augment_character(
    patch: np.ndarray, rng: np.random.Generator | None = None
) -> np.ndarray:
    """Small augmentation for a normalized character patch."""
    if patch is None or patch.size == 0:
        raise ValueError("patch is empty")
    rng = rng or np.random.default_rng()
    result = patch
    if rng.random() < 0.7:
        result = rotate(result, float(rng.uniform(-12, 12)))
    if rng.random() < 0.5:
        result = gaussian_blur(result, float(rng.uniform(0.0, 1.2)))
    if rng.random() < 0.5:
        result = brightness_contrast(
            result,
            float(rng.uniform(-30, 30)),
            float(rng.uniform(0.7, 1.3)),
        )
    return result
