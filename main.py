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
import sqlite3
from fastapi import Request



DAILY_LIMIT = 5

conn = sqlite3.connect("usage.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS usage (
    user_key TEXT,
    date TEXT,
    count INTEGER
)
""")

conn.commit()

def check_limit(user_key):

    today = str(date.today())

    cursor.execute("""
        SELECT count FROM usage
        WHERE user_key = ? AND date = ?
    """, (user_key, today))

    row = cursor.fetchone()

    # erster request heute
    if row is None:

        cursor.execute("""
            INSERT INTO usage (user_key, date, count)
            VALUES (?, ?, ?)
        """, (user_key, today, 1))

        conn.commit()

        remaining = DAILY_LIMIT - 1

        return True, remaining

    current_count = row[0]

    # limit erreicht
    if current_count >= DAILY_LIMIT:
        return False, 0

    # count erhöhen
    new_count = current_count + 1

    cursor.execute("""
        UPDATE usage
        SET count = ?
        WHERE user_key = ? AND date = ?
    """, (new_count, user_key, today))

    conn.commit()

    remaining = DAILY_LIMIT - new_count

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
async def bild_zu_text(
    request: Request,
    file: UploadFile = File(...),
    userId: str = Form(...)
):

    print("userId:", userId)

    ip = request.client.host

    user_key = f"{ip}_{userId}"

    allowed, remaining = check_limit(user_key)

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