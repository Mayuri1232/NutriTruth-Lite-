"""NutriTruth Lite - FastAPI entry point."""
import inspect
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import APP_NAME, STATIC_DIR, TEMPLATES_DIR, configure_tesseract, logger
from app.routes import api


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_tesseract()     # logs the resolved binary path at startup
    yield


app = FastAPI(title=APP_NAME, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.include_router(api.router)

# Starlette >= 0.28 wants TemplateResponse(request, name, context); older wants (name, context).
_NEW_TEMPLATE_API = "request" in list(inspect.signature(templates.TemplateResponse).parameters)[:1]


def render(request: Request, name: str, context: dict = None):
    context = dict(context or {})
    if _NEW_TEMPLATE_API:
        return templates.TemplateResponse(request, name, context)
    context["request"] = request
    return templates.TemplateResponse(name, context)


@app.get("/", include_in_schema=False)
def index(request: Request):
    return render(request, "index.html", {"app_name": APP_NAME})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": f"Internal server error: {exc}"})
