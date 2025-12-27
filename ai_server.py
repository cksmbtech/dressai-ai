from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
import base64
import time
import os

app = FastAPI()

# =========================
# CORS CONFIG
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten later if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# ENV VARIABLES
# =========================
STABLE_HORDE_API_KEY = os.getenv("STABLE_HORDE_API_KEY", "").strip()

print("DEBUG HORDE KEY PRESENT:", bool(STABLE_HORDE_API_KEY))
print("DEBUG HORDE KEY LENGTH:", len(STABLE_HORDE_API_KEY))

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
        # Read image
        image_bytes = await file.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # =========================
        # PROMPT (BEAUTIFUL FACE + BODY)
        # =========================
        prompt = (
              "Ultra realistic South Indian female fashion model wearing a silk saree "
              "matching the uploaded reference image in color, fabric texture and border design. "
              "Natural beautiful face, symmetrical features, smooth skin, elegant posture, "
              "real human proportions, studio catalog photography, professional soft lighting, "
              "DSLR photo, shallow depth of field, high fashion editorial style, "
              "photorealistic, extremely detailed fabric folds, no artificial look"
            )
            
            negative_prompt = (
              "ugly face, distorted face, fake skin, doll-like, plastic skin, "
              "anime, cartoon, illustration, cgi, unreal lighting, bad anatomy, "
              "extra fingers, deformed body, blur, low quality, painting"
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
        for _ in range(30):  # ~150 seconds max
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

