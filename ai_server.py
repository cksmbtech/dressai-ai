from fastapi import FastAPI, File, UploadFile, Form
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
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# ENV VARIABLES
# =========================
STABLE_HORDE_API_KEY = os.getenv("STABLE_HORDE_API_KEY", "").strip()

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
# PROMPT HELPERS
# =========================
def age_prompt(age_group: str) -> str:
    return {
        "Kids (5–12)": "young child model",
        "Teens (13–19)": "teenage fashion model",
        "20–30": "young adult fashion model",
        "30–45": "adult fashion model",
        "45+": "mature elegant fashion model"
    }.get(age_group, "adult fashion model")

def gender_prompt(gender: str) -> str:
    return {
        "Female": "female",
        "Male": "male",
        "Unisex": "androgynous"
    }.get(gender, "female")

# =========================
# AI GENERATION ENDPOINT
# =========================
@app.post("/generate")
async def generate_image(
    file: UploadFile = File(...),
    age_group: str = Form("20–30"),
    gender: str = Form("Female")
):
    try:
        # -------------------------
        # Read uploaded image
        # -------------------------
        image_bytes = await file.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        age_desc = age_prompt(age_group)
        gender_desc = gender_prompt(gender)

        # -------------------------
        # PROMPT (MATCH INPUT IMAGE)
        # -------------------------
        prompt = (
            f"Ultra realistic South Indian {gender_desc} {age_desc} "
            f"wearing a silk saree exactly matching the uploaded reference image. "
            f"Accurate saree color, border design, fabric texture, weave pattern, "
            f"and traditional draping style. "
            f"Beautiful symmetrical face, natural skin texture, soft facial expression, "
            f"realistic hands, arms, body proportions. "
            f"Professional studio fashion photography, DSLR quality, "
            f"soft diffused lighting, shallow depth of field, "
            f"catalog fashion shoot, photorealistic, no artificial look."
        )

        negative_prompt = (
            "ugly face, distorted face, asymmetrical face, deformed features, "
            "fake skin, plastic skin, doll-like, cgi, cartoon, anime, illustration, "
            "painting, unrealistic lighting, bad anatomy, extra limbs, "
            "extra fingers, missing fingers, malformed hands, "
            "blurry, low resolution, low quality"
        )

        payload = {
            "prompt": prompt,
            "params": {
                "sampler_name": "k_euler",
                "steps": 22,
                "cfg_scale": 7,
                "width": 512,
                "height": 768,
                "negative_prompt": negative_prompt
            },
            "nsfw": False,
            "trusted_workers": True,
            "source_image": image_b64
        }

        # -------------------------
        # SUBMIT TO STABLE HORDE
        # -------------------------
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

        # -------------------------
        # POLL RESULT
        # -------------------------
        for _ in range(30):  # ~150 sec
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
