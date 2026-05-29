from fastapi import FastAPI

app = FastAPI(title="Trestle API")

@app.get("/health")
async def health():
    return {"status": "ok"}
