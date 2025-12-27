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
    age_group: str = "adult",
    gender: str = "female"
):
    try:
        image_bytes = await file.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        age_group = age_group.lower()
        gender = gender.lower()

        # =========================
        # DYNAMIC PROMPT LOGIC
        # =========================

        if gender == "male":
            if "teen" in age_group:
                prompt = (
                    "Ultra realistic South Indian teenage boy wearing modern casual outfit "
                    "such as a stylish shirt and jeans. Masculine face, youthful features, "
                    "natural skin texture, realistic proportions, studio photography, "
                    "DSLR photo, professional lighting, photorealistic."
                )
            else:
                prompt = (
                    "Ultra realistic South Indian male fashion model wearing traditional "
                    "kurta or modern formal shirt and trousers. Handsome masculine face, "
                    "natural expression, realistic body proportions, studio fashion photography, "
                    "photorealistic, high detail."
                )

            negative_prompt = (
                "female clothing, saree, lehenga, blouse, makeup, feminine face, "
                "extra limbs, distorted face, cartoon, anime, cgi, unreal"
            )

        else:  # FEMALE
            if "teen" in age_group:
                prompt = (
                    "Ultra realistic South Indian teenage girl wearing elegant modern ethnic "
                    "or casual traditional outfit. Youthful beautiful face, natural skin, "
                    "realistic body proportions, studio photography, photorealistic."
                )
            else:
                prompt = (
                    "Ultra realistic South Indian woman wearing elegant silk saree matching "
                    "the uploaded reference image in color and fabric texture. Beautiful face, "
                    "symmetrical features, smooth natural skin, professional studio lighting, "
                    "DSLR fashion photography, photorealistic."
                )

            negative_prompt = (
                "male body, beard, moustache, masculine face, cartoon, anime, cgi, "
                "extra fingers, distorted body, fake skin"
            )

        # =========================
        # STABLE HORDE PAYLOAD
        # =========================
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

        submit = requests.post(
            "https://stablehorde.net/api/v2/generate/async",
            headers=HORDE_HEADERS,
            json=payload,
            timeout=30
        )

        if submit.status_code != 202:
            return JSONResponse(
                status_code=500,
                content={"error": "Stable Horde submit failed", "details": submit.json()}
            )

        request_id = submit.json()["id"]

        for _ in range(30):
            time.sleep(5)
            check = requests.get(
                f"https://stablehorde.net/api/v2/generate/status/{request_id}",
                headers=HORDE_HEADERS
            )
            data = check.json()

            if data.get("done"):
                gens = data.get("generations", [])
                if gens:
                    return {"image_base64": gens[0]["img"]}

        return JSONResponse(status_code=504, content={"error": "AI generation timed out"})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
