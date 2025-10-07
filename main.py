from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import pandas as pd
from parsers import get_parser
from common.bank_detect import detect_bank
from preview import preview_pdf

app = FastAPI(title="Bank PDF Parser", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/parse")
async def parse(file: UploadFile, password: str = Form(default=None), bank: str = Form(default=None)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            contents = await file.read()
            tmp.write(contents)
            pdf_path = tmp.name

        bank_guess = bank or (detect_bank(pdf_path, password) or "unknown")
        parser = get_parser(bank_guess)
        result = parser(pdf_path, password)

        if isinstance(result, dict) and "error" in result:
            return JSONResponse(content=result, status_code=400)

        return JSONResponse(content= result)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/preview")
async def preview(file: UploadFile, password: str = Form(default=None)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            contents = await file.read()
            tmp.write(contents)
            pdf_path = tmp.name

        result = preview_pdf(pdf_path, password)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)