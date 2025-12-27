from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
import base64
import time
import io
from PIL import Image

app = FastAPI()

# =========================
# CORS (VERY IMPORTANT)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# HEALTH CHECK (Render)
# =========================
@app.get("/healthz")
def health():
    return {"status": "ok"}

# =========================
# STABLE HORDE CONFIG
# =========================
HORDE_API = "https://stablehorde.net/api/v2"
CLIENT_AGENT = "dressai-demo/1.0"

# =========================
# AI GENERATE ENDPOINT
# =========================
@app.post("/generate")
async def generate_image(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Encode input image (reference only)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_b64 = base64.b64encode(buffer.getvalue()).decode()

        # =========================
        # STRONG FASHION PROMPT
        # =========================
        prompt = (
            "A beautiful South Indian fashion model wearing an elegant traditional saree. "
            "The saree fabric, color, and golden zari patterns closely match the uploaded reference image. "
            "Graceful posture, proportional body, natural hands and fingers, smooth realistic skin, "
            "beautiful symmetrical face, soft facial expression, professional studio fashion photography. "
            "High-end fashion catalog style, accurate saree draping, realistic fabric folds, "
            "cinematic lighting, sharp focus, ultra detailed, photorealistic."
        )

        negative_prompt = (
            "ugly face, deformed face, bad anatomy, extra fingers, extra hands, extra limbs, "
            "distorted body, cartoon, anime, blurry, low quality, oversharpened, harsh lighting"
        )

        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "params": {
                "sampler_name": "k_euler",
                "steps": 25,
                "cfg_scale": 7,
                "width": 512,
                "height": 768,
            },
            "nsfw": False,
            "trusted_workers": False,
            "models": ["Deliberate"],
            "source_image": img_b64,
        }

        headers = {
            "Content-Type": "application/json",
            "Client-Agent": CLIENT_AGENT,
        }

        # =========================
        # SUBMIT JOB
        # =========================
        submit = requests.post(
            f"{HORDE_API}/generate/async",
            json=payload,
            headers=headers,
            timeout=30,
        )

        submit_data = submit.json()
        if "id" not in submit_data:
            return JSONResponse(
                {"error": "Stable Horde submit failed", "details": submit_data},
                status_code=500,
            )

        job_id = submit_data["id"]

        # =========================
        # POLL RESULT
        # =========================
        for _ in range(40):
            time.sleep(3)
            check = requests.get(f"{HORDE_API}/generate/status/{job_id}", timeout=30)
            result = check.json()

            if result.get("done"):
                if result.get("generations"):
                    image_url = result["generations"][0]["img"]
                    return {"image_base64": image_url}
                else:
                    break

        return JSONResponse(
            {"error": "AI generation timed out"},
            status_code=504,
        )

    except Exception as e:
        return JSONResponse(
            {"error": "Server error", "details": str(e)},
            status_code=500,
        )
