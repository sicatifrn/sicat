from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.database import engine, Base, settings
from app.routers import auth, fichas, admin, public, bibliotecarios
from app.admin_sync import admin_sync_loop
from app.schema_sync import ensure_database_schema

logging.basicConfig(level=logging.INFO)

Base.metadata.create_all(bind=engine)
ensure_database_schema(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = asyncio.Event()
    task = None
    if settings.admin_sync_enabled:
        task = asyncio.create_task(admin_sync_loop(stop))
    yield
    if task:
        stop.set()
        await task


app = FastAPI(title="SICAT API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar diretório estático para servir arquivos
PUBLIC_DIR = Path(__file__).parent / "public"
PUBLIC_DIR.mkdir(exist_ok=True)
(PUBLIC_DIR / "pdfs").mkdir(exist_ok=True)
(PUBLIC_DIR / "imagens").mkdir(exist_ok=True)
app.mount("/public", StaticFiles(directory=str(PUBLIC_DIR)), name="public")

app.include_router(auth.router, prefix="/api/auth", tags=["autenticação"])
app.include_router(fichas.router, prefix="/api/fichas", tags=["fichas catalográficas"])
app.include_router(admin.router, prefix="/api/admin", tags=["administração"])
app.include_router(public.router, prefix="/api/public", tags=["público"])
app.include_router(bibliotecarios.router, prefix="/api/bibliotecarios", tags=["bibliotecários"])


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <!doctype html>
    <html lang="pt-BR">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>SICAT API</title>
        <style>
          :root {
            color-scheme: light;
            --bg: #f7f4ee;
            --card: #ffffff;
            --brand: #447fa8;
            --brand-dark: #345773;
            --muted: #637589;
            --border: #e1e7ee;
          }

          * {
            box-sizing: border-box;
          }

          body {
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            background:
              radial-gradient(circle at top left, rgba(85, 148, 196, 0.22), transparent 34rem),
              linear-gradient(135deg, #fdfcfa 0%, var(--bg) 100%);
            color: #263241;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          }

          main {
            width: min(92vw, 760px);
            padding: 2rem;
          }

          .card {
            background: rgba(255, 255, 255, 0.86);
            border: 1px solid var(--border);
            border-radius: 28px;
            box-shadow: 0 24px 70px rgba(52, 87, 115, 0.16);
            padding: clamp(1.5rem, 4vw, 3rem);
            backdrop-filter: blur(14px);
          }

          .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            border-radius: 999px;
            background: #eef6fb;
            color: var(--brand-dark);
            font-size: 0.875rem;
            font-weight: 700;
            padding: 0.5rem 0.85rem;
          }

          .dot {
            width: 0.65rem;
            height: 0.65rem;
            border-radius: 999px;
            background: #22c55e;
            box-shadow: 0 0 0 5px rgba(34, 197, 94, 0.14);
          }

          h1 {
            margin: 1.4rem 0 0.75rem;
            color: #1f2937;
            font-size: clamp(2.2rem, 8vw, 4.25rem);
            line-height: 0.95;
            letter-spacing: -0.055em;
          }

          p {
            margin: 0;
            color: var(--muted);
            font-size: clamp(1rem, 2vw, 1.15rem);
            line-height: 1.7;
          }

          .actions {
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-top: 2rem;
          }

          a {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 2.75rem;
            border-radius: 999px;
            padding: 0.75rem 1.15rem;
            text-decoration: none;
            font-weight: 700;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
          }

          a:hover {
            transform: translateY(-1px);
          }

          .primary {
            background: var(--brand);
            color: #fff;
            box-shadow: 0 12px 26px rgba(68, 127, 168, 0.25);
          }

          .secondary {
            border: 1px solid var(--border);
            color: var(--brand-dark);
            background: #fff;
          }

          footer {
            margin-top: 1.5rem;
            color: #7d8fa3;
            font-size: 0.9rem;
            text-align: center;
          }
        </style>
      </head>
      <body>
        <main>
          <section class="card" aria-label="Status da API SICAT">
            <span class="badge"><span class="dot"></span> API online</span>
            <h1>SICAT API</h1>
            <p>
              Serviço de integração do Sistema de Fichas Catalográficas do IFRN.
              A API está ativa e pronta para receber requisições do frontend.
            </p>
            <div class="actions">
              <a class="primary" href="/docs">Abrir documentação</a>
              <a class="secondary" href="/redoc">Ver ReDoc</a>
            </div>
          </section>
          <footer>Sistema Integrado de Catalogação</footer>
        </main>
      </body>
    </html>
    """

