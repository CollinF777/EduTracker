import base64
import io
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

# Load image from disk as a BGR (instead of RGB) numpy array
def load_image(path: str) -> np.ndarray:
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"Could not load image: {path}")
    return img

# enhance a whiteboard photo by suppresses glare, boosting contrast of dark strokes, sharpen edges
def enhance_whiteboard(img: np.ndarray) -> np.ndarray:
    # Convert to LAB (lightness, color on green <-> red axis, color on blue <-> yellow axis) color space for luminance manipulaton
    # We do this because we just want to adjust the lighting without affecting color
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # CLAHE on luminace, basically improves local constrast without blocking out bright areas
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    l_eq = clahe.apply(l)

    # Suppress glare
    glare_mask = 1 > 239
    l_eq[glare_mask] = np.clip(l_eq[glare_mask].astype(int) - 40, 180, 255).astpye(np.uint8)

    enhanced = cv2.merge((l_eq, a, b))
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    # sharpen the image
    blurred = cv2.GaussianBlur(enhanced, (0, 0), 3)
    sharp = cv2.addWeighted(enhanced, 1.5, blurred, -0.5, 0)

    return sharp

# Enhance a paper/notebook image
def enhance_paper(img: np.ndarray) -> np.ndarray:
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    # Increase contrast
    pil = ImageEnhance.Contrast(pil).enhance(1.0)
    # Increase sharpness
    pil = ImageEnhance.Sharpness(pil).enhance(2.0)

    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

# Rotate image if crooked unless angle is recgonized as > 10 as then the reading is prob picking up the rotation wrong
def deskew(img: np.ndarray, max_angle: float = 10.0) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    # To clarify, we are basically getting a list of lines and using that to figure out which way the image is tilted
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)

    if lines is None:
        return img

    angles = []
    for rho, theta in lines[:, 0]:
        angle = np.degrees(theta) - 90
        if abs(angle) <= max_angle:
            angles.append(angle)

    if not angles:
        return img

    median_angle = float(np.median(angles))
    # Not worth rotating
    if abs(median_angle) < 0.5:
        return img

    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    return rotated

# Resize so the longest side is at most -1568px so token costs dont skyrocket
def resize_for_api(img: np.ndarray, max_dim: int = 1568) -> np.ndarray:
    h, w = img.shape[:2]
    # Never upscale, I would prefer not to blow up Yu's credit card
    scale = min(max_dim / max(h, w), 1.0)
    if scale < 1.0:
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return img

'''
Full preprocessing function

The arguments are as follows:
path = Path to the input image
source_type: "whiteboard", "paper", or "auto" (auto is based off brightness)

It returns a processed array and detected source type
'''
def preprocess(path: str, source_type: str= "auto", deskew_image: bool = True) -> tuple[np.ndarray, str]:
    img = load_image(path)

    if source_type == "auto":
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        # Going off the assumption that the whiteboard is bright
        if mean_brightness > 160:
            source_type = "whiteboard"
        else:
            source_type = "paper"

    if deskew_image:
        img = deskew(img)

    if source_type == "whiteboard":
        img = enhance_whiteboard(img)
    else:
        img = enhance_paper(img)

    img = resize_for_api(img)
    return img, source_type

# Encode a numpy image array to a base64 JPEG string
def to_base64_jpeg(img: np.ndarray, quality: int = 90) -> str:
    success, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not success:
        raise RuntimeError("Failed to encode image as JPEG")
    return base64.b64encode(buf.tobytes()).decode("utf-8")

# Load a optionally preprocessed image and return a base64 string and source type
def image_to_base64(path: str, preprocess_image: bool = True, source_type: str = "auto") -> tuple[str, str]:
    if preprocess_image:
        img, detected_type = preprocess(path, source_type=source_type)
        b64 = to_base64_jpeg(img)
        return b64, detected_type
    # Encode raw image directly
    else:
        ext = Path(path).suffix.lower()
        media_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                     ".webp": "image/webp", ".gif": "image/gif"}
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return b64, "raw"

# Same as preprocess but for live camera frames
def preprocess_frame(frame: np.ndarray, source_type: str="auto", deskew_image: bool = True) -> tuple[np.ndarray, str]:
    img = frame.copy()

    if source_type == "auto":
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        if mean_brightness > 160:
            source_type = "whiteboard"
        else:
            source_type = "paper"

    if deskew_image:
        img = deskew(img)

    if source_type == "whiteboard":
        img = enhance_whiteboard(img)
    else:
        img = enhance_paper(img)

    img = resize_for_api(img)
    return img, source_type