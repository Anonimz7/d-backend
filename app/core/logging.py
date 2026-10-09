"""Centralized logging untuk Apk-Final unified backend.

Tujuan: visibilitas ke production tanpa mengubah perilaku API.
- Request log: method, path, status, durasi (tanpa body/query sensitif)
- Auth failures: username/email yang gagal (tanpa password)
- Unhandled exceptions: traceback penuh

Penggunaan:
    from app.core.logging import get_logger
    logger = get_logger("n6.auth")
    logger.info("login berhasil", extra={"user": username})
    logger.warning("login gagal", extra={"user": username})

Level via env LOG_LEVEL (default INFO).
"""

import logging
import os
import sys
import time
from typing import Callable

_configured = False


def setup_logging(level: str = None) -> None:
    """Konfigurasi root logger sekali saja. Idempotent."""
    global _configured
    if _configured:
        return

    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    numeric = getattr(logging, log_level, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(numeric)
    # Hindari duplikat handler bila dipanggil ulang
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)

    # Redam noise dari uvicorn access log (kita punya middleware sendiri)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Ambil logger bernama 'apkfinal.<name>'."""
    setup_logging()
    return logging.getLogger(f"apkfinal.{name}")


# --- Request logging middleware ---

# Path yang tidak perlu di-log setiap request (health check, docs)
SKIP_PATHS = {"/docs", "/openapi.json", "/redoc", "/favicon.ico"}


def request_logging_middleware(app):
    """Pasang middleware pencatat request. Panggil sekali di main.py."""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request

    logger = get_logger("http")

    class LoggingMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Callable):
            # Skip path yang noisy
            if request.url.path in SKIP_PATHS or request.url.path.startswith("/docs"):
                return await call_next(request)

            start = time.perf_counter()
            try:
                response = await call_next(request)
                status = response.status_code
            except Exception:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.exception(
                    "unhandled %s %s (%.1fms)",
                    request.method, request.url.path, duration_ms,
                )
                raise

            duration_ms = (time.perf_counter() - start) * 1000

            # Log level berdasarkan status
            msg = "%s %s -> %d (%.1fms)"
            args = (request.method, request.url.path, status, duration_ms)
            if status >= 500:
                logger.error(msg, *args)
            elif status >= 400:
                logger.warning(msg, *args)
            else:
                logger.info(msg, *args)

            return response

    app.add_middleware(LoggingMiddleware)
    return app
