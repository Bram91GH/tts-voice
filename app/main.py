import uvicorn
from fastapi import FastAPI

from services.call import router as call_router
from services.ai_parser import router as ai_router

app = FastAPI(title="Voice Agent")

app.include_router(call_router)
app.include_router(ai_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5050, reload=True)
