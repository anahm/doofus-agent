"""
Generate a standardized constellation flashcard set using Runware.

Prereqs:
  pip install runware requests
  export RUNWARE_API_KEY="your_api_key_here"

Docs:
  - Runware Python SDK usage: imageInference() with IImageInference :contentReference[oaicite:1]{index=1}
  - Image Inference API parameters (positivePrompt, width/height, model, outputFormat, numberResults) :contentReference[oaicite:2]{index=2}
"""

import os
import uuid
import asyncio
from pathlib import Path

import requests
from runware import Runware, IImageInference, IOpenAIProviderSettings

# -------------------------
# 1) CONFIG
# -------------------------

RUNWARE_API_KEY = os.getenv("RUNWARE_API_KEY")
if not RUNWARE_API_KEY:
    raise RuntimeError("Missing RUNWARE_API_KEY env var. Set it before running.")

# Pick a model you have access to.
# Example from Runware docs uses "runware:101@1" :contentReference[oaicite:3]{index=3}
MODEL_ID = os.getenv("RUNWARE_MODEL", "runware:101@1")

OUT_DIR = Path("constellation_cards")
OUT_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOAD_FILES = True  # set False if you only want URLs

# Your prompt template (no labels, square, thin constellation lines, translucent brush myth overlay)
PROMPT_TEMPLATE = """Create a square 1:1 minimalist astronomy flashcard image of the constellation [CONSTELLATION NAME].

Black background with subtle scattered small white background stars.

The main constellation stars should be brighter white and connected with very thin, clean white lines.

Overlay a large, highly translucent, hand-drawn paintbrush style illustration of the mythological figure associated with [CONSTELLATION NAME], aligned so the constellation stars map onto the figure naturally.

The figure should look wispy, ethereal, and semi-transparent — like faint chalk or watercolor brush strokes in white.

The brush lines should be loose, organic, and slightly imperfect — not sharp vector lines.

The constellation lines and stars should remain clearly visible above the figure.

No text, no labels, no borders, no decorative effects. Center the composition with generous negative space around it.

Maintain a consistent style suitable for a full 20-card flashcard deck.
"""

NEGATIVE_PROMPT = (
    "text, letters, words, label, caption, watermark, logo, border, frame, "
    "colorful nebula, galaxy swirl, lens flare, heavy glow, cartoon, 3d render"
)

CONSTELLATIONS = [
    # "Orion",
    # "Ursa Major",
    "Ursa Minor",
    "Cassiopeia",
    "Scorpius",
    "Leo",
    "Taurus",
    "Gemini",
    "Cygnus",
    "Lyra",
    "Andromeda",
    "Pegasus",
    "Sagittarius",
    "Aquarius",
    "Capricornus",
    "Virgo",
    "Aries",
    "Cancer",
    "Canis Major",
    "Crux",
]

# Generation parameters (tweak if needed)
WIDTH = 1024
HEIGHT = 1024
STEPS = 30
CFG_SCALE = 7.5
OUTPUT_FORMAT = "png"  # "jpg" also supported :contentReference[oaicite:4]{index=4}


# -------------------------
# 2) HELPERS
# -------------------------

def build_prompt(constellation: str) -> str:
    return PROMPT_TEMPLATE.replace("[CONSTELLATION NAME]", constellation)


def safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name).strip("_").lower()


def download_image(url: str, dest_path: Path) -> None:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    dest_path.write_bytes(r.content)


# -------------------------
# 3) MAIN
# -------------------------

async def main():
    runware = Runware(api_key=RUNWARE_API_KEY)
    await runware.connect()  # establishes the websocket connection :contentReference[oaicite:5]{index=5}

    for constellation in CONSTELLATIONS:
        prompt = build_prompt(constellation)

        req = IImageInference(
            taskUUID=str(uuid.uuid4()),
            model="openai:4@1",
            positivePrompt=prompt,
            width=1024,
            height=1024,
            numberResults=1,
            outputType="URL",
            outputFormat="png",
            providerSettings=IOpenAIProviderSettings(
                quality="high",
                background="opaque",
            ),
        )

        images = await runware.imageInference(requestImage=req)  # :contentReference[oaicite:6]{index=6}
        if not images:
            print(f"[{constellation}] No images returned.")
            continue

        url = images[0].imageURL
        print(f"[{constellation}] {url}")

        if DOWNLOAD_FILES:
            fname = f"{safe_filename(constellation)}.{OUTPUT_FORMAT}"
            path = OUT_DIR / fname
            download_image(url, path)
            print(f"  saved -> {path}")

    # Optional: close connection if the SDK exposes it (not required in many examples)
    # await runware.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

