from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import signals, score, whatif, execute, fivetran, chat

app = FastAPI(
    title="Nerve API",
    description="Autonomous D2C Financial Intelligence Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(signals.router, prefix="/api")
app.include_router(score.router, prefix="/api")
app.include_router(whatif.router, prefix="/api")
app.include_router(execute.router, prefix="/api")
app.include_router(fivetran.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

@app.get("/")
def root():
    return {"status": "Nerve is alive", "version": "1.0.0"}
