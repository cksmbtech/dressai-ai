from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
import io, requests, time

app = FastAPI()

# -----------------------------
# CORS
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
# SIMPLE COLOR DETECTION (NO NUMPY)
# -----------------------------
def extract_dominant_color(img: Image.Image):
    img = img.resize((50, 50))
    pixels = img.getdata()

    r = g = b = 0
    for px in pixels:
        r += px[0]
        g += px[1]
        b += px[2]

    total = len(pixels)
    r, g, b = r / total, g / total, b / total

    if r > g and r > b:
        return "red"
    if g > r and g > b:
        return "green"
    if b > r and b > g:
        return "blue"
    return "multicolor"

def build_prompt(color):
    return f"""
Ultra realistic studio photograph of a South Indian female fashion model,
wearing a {color} traditional silk saree with gold zari work,
realistic fabric texture, elegant draping,
neutral studio background, professional fashion lighting,
high detail, photorealistic, catalog photography.
"""

NEGATIVE_PROMPT = """
cartoon, anime, illustration, western dress, gown, suit,
bad anatomy, extra limbs, distorted face,
blurry, watermark, logo, text
"""

# -----------------------------
# GENERATE ENDPOINT
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
        "models": ["stable_diffusion"]
    }

    headers = {
        "Content-Type": "application/json",
        "apikey": "zKW_0W2Zy9IK8sfAKXPKjQ"  # anonymous
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
    for _ in range(20):
        time.sleep(5)
        status = requests.get(
            f"https://stablehorde.net/api/v2/generate/status/{job_id}"
        ).json()

        if status.get("done") and status.get("generations"):
            return {"image_base64": status["generations"][0]["img"]}

    return JSONResponse({"error": "AI generation timed out"}, status_code=504)
