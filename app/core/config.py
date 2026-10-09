"""Konfigurasi terpusat backend gabungan Apk-Final.

Satu file .env untuk kelima aplikasi. Tiap aplikasi memakai schema
PostgreSQL sendiri (haylen, n6, dbacc, dbfin, clx) dalam satu database.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database: satu database, lima schema (lihat app.core.database.APP_SCHEMAS)
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/apkfinal"

    # JWT tunggal untuk semua aplikasi (klaim "app" membedakan pemilik token)
    JWT_SECRET: str = "ganti-dengan-secret-acak-min-32-karakter"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    CORS_ORIGINS: str = "*"

    # Seed owner per aplikasi (dibuat otomatis saat startup bila belum ada)
    HAYLEN_OWNER_USERNAME: str = "owner"
    HAYLEN_OWNER_PASSWORD: str = "owner123"
    HAYLEN_OWNER_NAME: str = "Owner Haylen"

    N6_OWNER_USERNAME: str = "owner"
    N6_OWNER_PASSWORD: str = "owner123"
    N6_OWNER_NAME: str = "Owner N6"

    DBACC_OWNER_EMAIL: str = "owner@dbacc.local.id"
    DBACC_OWNER_PASSWORD: str = "owner123"
    DBACC_OWNER_NAME: str = "Owner DB Accounting"

    DBFIN_OWNER_USERNAME: str = "owner"
    DBFIN_OWNER_PASSWORD: str = "owner123"
    DBFIN_OWNER_NAME: str = "Owner DB Finance"

    CLX_OWNER_USERNAME: str = "owner"
    CLX_OWNER_PASSWORD: str = "owner123"
    CLX_OWNER_NAME: str = "Owner Claisrox"


settings = Settings()
