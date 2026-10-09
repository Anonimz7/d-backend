"""Backend gabungan Apk-Final: 1 proses FastAPI untuk 5 aplikasi.

Namespace:
    /api/haylen/*    -> Haylen (sekolah renang)
    /api/n6/v1/*      -> N6 (dashboard kepelatihan)
    /api/dbacc/*      -> DB Accounting
    /api/dbfin/*      -> DB Finance
    /api/claisrox/*   -> Claisrox (operasional produksi)

Jalankan:  uvicorn app.main:app --reload   (dari folder unified-backend/)
Dokumen:   http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.apps.claisrox.router import router as claisrox_router
from app.apps.claisrox.seed import ensure_owner as claisrox_owner
from app.apps.dbacc.router import router as dbacc_router
from app.apps.dbacc.seed import ensure_owner as dbacc_owner
from app.apps.dbfin.router import router as dbfin_router
from app.apps.dbfin.seed import ensure_owner as dbfin_owner
from app.apps.haylen.router import router as haylen_router
from app.apps.haylen.seed import ensure_owner as haylen_owner
from app.apps.n6.router import router as n6_router
from app.apps.n6.seed import ensure_owner as n6_owner
from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.core.logging import setup_logging, get_logger, request_logging_middleware

# Setup centralized logging sepagi mungkin
setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting up, init_db()")
    init_db()
    db = SessionLocal()
    try:
        haylen_owner(db)
        n6_owner(db)
        dbacc_owner(db)
        dbfin_owner(db)
        claisrox_owner(db)
        db.commit()
        logger.info("owner seeds ensured")
    finally:
        db.close()
    yield
    logger.info("shutting down")


app = FastAPI(title="Apk-Final Unified API", lifespan=lifespan)

# Request logging (method, path, status, durasi)
request_logging_middleware(app)

origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(haylen_router, prefix="/api/haylen")
app.include_router(n6_router, prefix="/api/n6")
app.include_router(dbacc_router, prefix="/api/dbacc")
app.include_router(dbfin_router, prefix="/api/dbfin")
app.include_router(claisrox_router, prefix="/api/claisrox")


@app.get("/health")
def health():
    return {"status": "ok", "apps": ["haylen", "n6", "dbacc", "dbfin", "claisrox"]}
