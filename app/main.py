from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from routers import router

app = FastAPI(title="Citation Tools API", version="0.1.0")

# CORS cho FE (dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount router với prefix /api/v1
app.include_router(router.router, prefix="/api/v1", tags=["citations"])

@app.get("/")
def root():
    return {"name": "Citation Tools API", "version": "0.1.0"}

@app.get("/healthz")
def healthz():
    return {"status": "ok"}
