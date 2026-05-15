#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi import Form
import anthropic
import base64
import io
from PIL import Image
import pillow_heif
import os
from dotenv import load_dotenv
load_dotenv()
from datetime import date
from fastapi import HTTPException

usage = {}

DAILY_LIMIT = 5

def check_limit(user_id):
    today = str(date.today())

    if user_id not in usage:
        usage[user_id] = {"count": 0, "date": today}

    if usage[user_id]["date"] != today:
        usage[user_id] = {"count": 0, "date": today}

    remaining = DAILY_LIMIT - usage[user_id]["count"]

    if remaining <= 0:
        return False, 0

    usage[user_id]["count"] += 1
    remaining = DAILY_LIMIT - usage[user_id]["count"]

    return True, remaining

pillow_heif.register_heif_opener()



app = FastAPI()


@app.get("/api/status")
async def get_status(userId: str):
    today = str(date.today())

    if userId not in usage:
        usage[userId] = {"count": 0, "date": today}

    if usage[userId]["date"] != today:
        usage[userId] = {"count": 0, "date": today}

    remaining = DAILY_LIMIT - usage[userId]["count"]

    return {"remaining": remaining}

client = anthropic.Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"]
)

@app.post("/api/bild-zu-text")
async def bild_zu_text(file: UploadFile = File(...),userId: str = Form(...)):

    print("userId:", userId)

    allowed, remaining = check_limit(userId)

    if not allowed:
        return {"error": "daily_limit_reached", "remaining": 0}


    inhalt = await file.read()

    # 🧼 Bild normalisieren
    try:
        bild = Image.open(io.BytesIO(inhalt))
        bild = bild.convert("RGB")

        buffer = io.BytesIO()
        bild.save(buffer, format="JPEG", quality=90)
        jpeg_bytes = buffer.getvalue()

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Bild konnte nicht verarbeitet werden: {e}"
        )

    # 📦 Base64 encoding
    bild_base64 = base64.b64encode(jpeg_bytes).decode("utf-8")

    # 🤖 Claude request
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": bild_base64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                           """
Extract the handwritten mathematical notes from the image and convert them into clean LaTeX.

Requirements:
- Return ONLY valid LaTeX equations
- No markdown
- No code fences
- No explanations
- No \\documentclass
- No \\begin{document}
- No \\end{document}
- Do NOT include \\begin{aligned}
- Do NOT include \\end{aligned}

Formatting:
- Use proper mathematical LaTeX
- Preserve the structure from the notes
- Use line breaks with \\\\
- Keep multiline equations readable

Example:

x &= 2 \\\\
y &= 3 \\\\
z &= x + y

Return only the equations.
"""
                   
                        )
                    }
                ],
            }
        ],
    )

    latex = message.content[0].text.strip()

    return {
        "latex": latex,
        "remaining": remaining
    }


# 🌐 Frontend hosting
app.mount("/", StaticFiles(directory="static", html=True), name="static")