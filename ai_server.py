from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import base64
import time
import os

# =========================
# CONFIG
# =========================
HORDE_API_KEY = os.getenv("HORDE_API_KEY", zKW_0W2Zy9IK8sfAKXPKjQ
HORDE_SUBMIT_URL = "https://stablehorde.net/api/v2/generate/async"
HORDE_STATUS_URL = "https://stablehorde.net/api/v2/generate/status/"

# =========================
# APP INIT
# =========================
app = FastAPI()

# =========================
# CORS (CRITICAL FOR BROWSER)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cksmbtech.com",
        "https://www.cksmbtech.com",
        "*"   # keep during demo; restrict later
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# HEALTH CHECK
# =========================
@app.get("/")
def health():
    return {"status": "DressAI API running"}

# =========================
# GENERATE AI PREVIEW
# =========================
@app.post("/generate")
async def generate(file: UploadFile = File(...)):

    try:
        # Read uploaded image
        image_bytes = await file.read()
        image_b64 = base64.b64encode(image_bytes).decode()

        # Prompt (you can tune later)
        prompt = (
            "A professional fashion model wearing a dress inspired by the uploaded image. "
            "Studio lighting, realistic fabric texture, high quality fashion photography, "
            "neutral background, full body, realistic proportions."
        )

        # -------------------------
        # SUBMIT TO STABLE HORDE
        # -------------------------
        submit_response = requests.post(
            HORDE_SUBMIT_URL,
            headers={
                "apikey": HORDE_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "prompt": prompt,
                "params": {
                    "width": 512,
                    "height": 512,
                    "steps": 15,
                    "sampler_name": "k_euler"
                },
                "models": ["stable_diffusion"],
                "nsfw": False,
                "slow_workers": True
            },
            timeout=30
        )

        if submit_response.status_code != 202:
            return JSONResponse({
                "error": "Stable Horde submit failed",
                "details": submit_response.text
            }, status_code=500)

        job_id = submit_response.json().get("id")

        # -------------------------
        # POLL FOR RESULT
        # -------------------------
        for _ in range(24):  # ~2 minutes max
            time.sleep(5)

            status_response = requests.get(
                HORDE_STATUS_URL + job_id,
                timeout=30
            ).json()

            if status_response.get("done"):
                generations = status_response.get("generations", [])

                if not generations:
                    return JSONResponse({
                        "error": "No image generated"
                    }, status_code=500)

                # Stable Horde returns a public image URL
                return JSONResponse({
                    "image_base64": generations[0]["img"]
                })

        return JSONResponse({
            "error": "AI generation timed out"
        }, status_code=504)

    except Exception as e:
        return JSONResponse({
            "error": "Server error",
            "details": str(e)
        }, status_code=500)
