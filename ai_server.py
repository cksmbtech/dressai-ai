from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
import base64
import time
import os

app = FastAPI()

# =========================
# CORS (VERY IMPORTANT)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # you can restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# ENV VARIABLES
# =========================
STABLE_HORDE_API_KEY = os.getenv("STABLE_HORDE_API_KEY")

if not STABLE_HORDE_API_KEY:
    print("⚠️ WARNING: STABLE_HORDE_API_KEY not set")

HORDE_HEADERS = {
    "apikey": STABLE_HORDE_API_KEY,
    "Client-Agent": "dressai/1.0 (cksmbtech.com)",
    "Content-Type": "application/json"
}

# =========================
# HEALTH CHECK
# =========================
@app.get("/healthz")
def health():
    return {"status": "ok"}

# =========================
# AI GENERATION ENDPOINT
# =========================
@app.post("/generate")
async def generate_image(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # 🔥 PROMPT (BEAUTIFUL FACE + BODY)
        prompt = (
            "A beautiful South Indian woman fashion model wearing an elegant saree, "
            "graceful posture, symmetrical attractive face, clear smooth skin, "
            "natural expression, studio fashion photography, professional lighting, "
            "high realism, detailed fabric texture, accurate saree draping, "
            "photorealistic, catalog quality, ultra high detail"
        )

        negative_prompt = (
            "ugly face, deformed face, bad anatomy, extra limbs, extra fingers, "
            "crooked eyes, distorted face, blurry, low quality, cartoon, anime, "
            "overexposed, underexposed, bad hands, bad proportions"
        )

        payload = {
            "prompt": prompt,
            "params": {
                "sampler_name": "k_euler",
                "steps": 20,
                "cfg_scale": 7,
                "width": 512,
                "height": 768,
                "negative_prompt": negative_prompt
            },
            "nsfw": False,
            "trusted_workers": True,
            "source_image": image_b64
        }

        # =========================
        # SUBMIT TO STABLE HORDE
        # =========================
        submit = requests.post(
            "https://stablehorde.net/api/v2/generate/async",
            headers=HORDE_HEADERS,
            json=payload,
            timeout=30
        )

        if submit.status_code != 202:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Stable Horde submit failed",
                    "details": submit.json()
                }
            )

        request_id = submit.json()["id"]

        # =========================
        # POLL RESULT
        # =========================
        for _ in range(30):
            time.sleep(5)

            check = requests.get(
                f"https://stablehorde.net/api/v2/generate/status/{request_id}",
                headers=HORDE_HEADERS
            )

            data = check.json()

            if data.get("done"):
                generations = data.get("generations", [])
                if generations:
                    return {
                        "image_base64": generations[0]["img"]
                    }

        return JSONResponse(
            status_code=504,
            content={"error": "AI generation timed out"}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Server error", "details": str(e)}
        )
