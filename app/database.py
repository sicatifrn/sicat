from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_hours: int = 72
    suap_api_url: str = "https://suap.ifrn.edu.br"
    # Defaults de teste. Se algum dia houver acesso ao painel do CapRover,
    # basta definir as env vars lá que elas sobrescrevem estes valores.
    suap_client_id: str = "l6nHv9ox0vtKkFXfvzASSPximbLsFPf1rYEu60Rv"
    suap_client_secret: str = "Xt0DzcUPiYp0QSxuAyjK91gu9qrHwmZGllzBR6Hewx3KjWAU3matZXTIxK6zu9wRMutANsteT1UevcrBtaJi9CrJZIN3QhCAZCNVkzkUD1emLpx7IGnleXwHsvyFfjwr"
    suap_redirect_uri: str = "https://sicat.ifrn.edu.br/api/auth/suap/callback"
    suap_oauth_scope: str = "identificacao email documentos_pessoais"
    frontend_url: str = "https://sicat.ifrn.edu.br"
    # Matrículas (separadas por vírgula) que passam a admin ao registar ou ao iniciar sessão.
    admin_matriculas: str = Field(
        default="20221041110028",
        description="Lista opcional; sobrescreve com env ADMIN_MATRICULAS",
    )
    # Intervalo em segundos para reforçar admin no BD (cron interno).
    admin_sync_interval_seconds: int = Field(default=300, ge=30)
    admin_sync_enabled: bool = True

    class Config:
        env_file = ".env"

settings = Settings()


def matriculas_admin_configuradas() -> set[str]:
    raw = (settings.admin_matriculas or "").strip()
    if not raw:
        return set()
    return {m.strip() for m in raw.split(",") if m.strip()}

connect_args = {}
if 'pymysql' in settings.database_url:
    connect_args = {
        'connect_timeout': 120,
        'read_timeout': 600,
        'write_timeout': 600,
        'charset': 'utf8mb4'
    }

engine = create_engine(
    settings.database_url,
    echo=True,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

