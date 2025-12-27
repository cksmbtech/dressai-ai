from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
import io, requests, base64, time, os
import numpy as np

app = FastAPI()

# -----------------------------
# CORS (IMPORTANT)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "DressAI API running"}

# -----------------------------
# IMAGE ANALYSIS
# -----------------------------
def extract_dominant_color(image: Image.Image):
    image = image.resize((100, 100))
    arr = np.array(image)
    avg = arr.mean(axis=(0, 1))

    r, g, b = avg
    if r > g and r > b:
        return "red"
    if g > r and g > b:
        return "green"
    if b > r and b > g:
        return "blue"
    return "multicolor"

def build_prompt(color: str):
    return f"""
Ultra realistic studio photograph of a South Indian female fashion model,
wearing a {color} traditional Indian silk saree with gold zari detailing,
inspired by South Indian wedding wear.
Elegant drape, realistic fabric folds, high detail textile texture,
neutral studio background, soft professional lighting,
fashion catalog photography, photorealistic, sharp focus.
"""

NEGATIVE_PROMPT = """
cartoon, anime, illustration, low quality, bad anatomy,
extra limbs, distorted face, western gown, suit, jeans,
blurry, cropped, watermark, logo, text
"""

# -----------------------------
# AI GENERATION (STABLE HORDE)
# -----------------------------
@app.post("/generate")
async def generate(file: UploadFile = File(...)):

    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    color = extract_dominant_color(image)
    prompt = build_prompt(color)

    payload = {
        "prompt": prompt,
        "params": {
            "sampler_name": "k_euler",
            "steps": 25,
            "cfg_scale": 7,
            "width": 512,
            "height": 768,
            "negative_prompt": NEGATIVE_PROMPT
        },
        "nsfw": False,
        "models": ["stable_diffusion"],
    }

    headers = {
        "Content-Type": "application/json",
        "apikey": "zKW_0W2Zy9IK8sfAKXPKjQ"  # anonymous stable horde
    }

    submit = requests.post(
        "https://stablehorde.net/api/v2/generate/async",
        json=payload,
        headers=headers
    ).json()

    if "id" not in submit:
        return JSONResponse(
            {"error": "Stable Horde submit failed", "details": submit},
            status_code=500
        )

    job_id = submit["id"]

    # Poll result
    for _ in range(25):
        time.sleep(5)
        check = requests.get(
            f"https://stablehorde.net/api/v2/generate/status/{job_id}"
        ).json()

        if check.get("done") and check.get("generations"):
            img_url = check["generations"][0]["img"]
            return {"image_base64": img_url}

    return JSONResponse(
        {"error": "AI generation timed out"},
        status_code=504
    )
