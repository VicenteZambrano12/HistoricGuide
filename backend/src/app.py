from fastapi import FastAPI

from src.api.Endpoint.chat import router as chat_router
from src.api.Endpoint.health import router as health_router


app = FastAPI(title="HistoricGuide API")
app.include_router(health_router)
app.include_router(chat_router)