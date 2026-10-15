from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.database import engine
from app.core.redis import redis_client
from app.api.auth import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Старт: поки що нічого не ініціалізуємо
    yield
    # Зупинка: закриваємо пул з'єднань
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(
    title="Integrations Hub API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(auth_router)