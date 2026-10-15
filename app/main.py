"""Backend gabungan: 1 proses FastAPI untuk 4 aplikasi.

Namespace:
    /api/dbn6sport/v1/* -> dash-n6sport (dashboard kepelatihan)
    /api/dbacc/*        -> DB Accounting
    /api/dbfin/*        -> DB Finance
    /api/claisrox/*     -> Claisrox (operasional produksi)

Jalankan:  uvicorn app.main:app --reload   (dari folder d-backend/)
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
from app.apps.dbn6sport.router import router as dbn6sport_router
from app.apps.dbn6sport.seed import ensure_basics as dbn6sport_seed
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
        dbn6sport_seed(db)
        dbacc_owner(db)
        dbfin_owner(db)
        claisrox_owner(db)
        db.commit()
        logger.info("owner seeds ensured")
    finally:
        db.close()
    yield
    logger.info("shutting down")


app = FastAPI(title="d-backend Unified API", lifespan=lifespan)

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

app.include_router(dbn6sport_router, prefix="/api/dbn6sport/v1")
app.include_router(dbacc_router, prefix="/api/dbacc")
app.include_router(dbfin_router, prefix="/api/dbfin")
app.include_router(claisrox_router, prefix="/api/claisrox")


@app.get("/health")
def health():
    return {"status": "ok", "apps": ["dbn6sport", "dbacc", "dbfin", "claisrox"]}
