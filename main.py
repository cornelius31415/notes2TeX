#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
import anthropic
import base64
import io
from PIL import Image
import pillow_heif
import os
from dotenv import load_dotenv
load_dotenv()

pillow_heif.register_heif_opener()



app = FastAPI()

# ⚠️ DEV ONLY (später in .env verschieben!)
client = anthropic.Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"]
)

@app.post("/api/bild-zu-text")
async def bild_zu_text(file: UploadFile = File(...)):
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
- Return ONLY valid LaTeX
- No markdown
- No code fences
- No explanations
- No \\documentclass
- No \\begin{document}
- No \\end{document}

Formatting:
- Use proper mathematical LaTeX
- Preserve the structure from the notes
- Use line breaks with \\\\
- Format equations cleanly for aligned rendering
- Keep multiline equations readable

Example format:

x &= 2 \\\\
y &= 3 \\\\
z &= x + y

Return only the LaTeX content.
"""
                   
                        )
                    }
                ],
            }
        ],
    )

    latex = message.content[0].text.strip()

    return {
        "latex": latex
    }


# 🌐 Frontend hosting
app.mount("/", StaticFiles(directory="static", html=True), name="static")