from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import requests
import tempfile
import base64
import time
import os

app = FastAPI()

HORDE_API_KEY = "zKW_0W2Zy9IK8sfAKXPKjQ"  # use your key or anonymous

@app.post("/generate")
async def generate_image(file: UploadFile = File(...)):
    try:
        # Save temp image
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        os.remove(tmp_path)

        prompt = (
            "A professional fashion model wearing a modern dress, "
            "studio lighting, realistic fabric folds, high quality fashion photography"
        )

        submit_res = requests.post(
    "https://stablehorde.net/api/v2/generate/async",
    headers={
        "apikey": HORDE_API_KEY,
        "Content-Type": "application/json"
    },
    json={
        "prompt": prompt,
        "params": {
            "width": 512,
            "height": 512,
            "steps": 20,
            "cfg_scale": 7,
            "sampler_name": "k_euler"
        },
        "models": ["stable_diffusion"],
        "nsfw": False
    },
    timeout=30
)


        submit_json = submit_res.json()

        if "id" not in submit_json:
            return JSONResponse(
                status_code=500,
                content={"error": "Stable Horde submit failed", "details": submit_json}
            )

        job_id = submit_json["id"]

        # Poll for result
        for _ in range(20):  # max wait ~60s
            time.sleep(3)

            status_res = requests.get(
                f"https://stablehorde.net/api/v2/generate/status/{job_id}",
                timeout=30
            )

            status_json = status_res.json()

            if status_json.get("done"):
                gens = status_json.get("generations", [])
                if not gens:
                    return JSONResponse(
                        status_code=500,
                        content={"error": "No generations returned", "details": status_json}
                    )

                image_base64 = gens[0].get("img")
                if not image_base64:
                    return JSONResponse(
                        status_code=500,
                        content={"error": "Image missing", "details": gens[0]}
                    )

                return JSONResponse({"image_base64": image_base64})

        return JSONResponse(
            status_code=504,
            content={"error": "AI generation timed out"}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Server exception", "details": str(e)}
        )
