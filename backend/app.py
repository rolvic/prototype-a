"""Prototype A — Person Registry API.

A FastAPI backend for managing person records.
Connects to PostgreSQL for storage and Redis for caching.
"""

import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
import redis as redis_lib

app = FastAPI(
    title="Prototype A — Person Registry",
    description="Simple person registration system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
REDIS_URL = os.environ.get("REDIS_URL", "")
APP_NAME = os.environ.get("APP_NAME", "Prototype A")
APP_ENV = os.environ.get("APP_ENV", "development")


def get_db():
    """Get a database connection."""
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="DATABASE_URL not configured")
    return psycopg2.connect(DATABASE_URL)


def get_cache():
    """Get Redis connection. Returns None if not available."""
    if not REDIS_URL:
        return None
    try:
        return redis_lib.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        return None


def init_db():
    """Initialize database tables."""
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not set — skipping DB init")
        return
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS persons (
                id SERIAL PRIMARY KEY,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                email VARCHAR(100) UNIQUE,
                phone VARCHAR(20),
                age INTEGER CHECK (age > 0 AND age < 150),
                city VARCHAR(100),
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_persons_email ON persons(email)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_persons_name ON persons(last_name, first_name)
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")


# Initialize on startup
init_db()


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{app_name} — Registro de Personas</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; color: #333; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px 0; text-align: center; }}
        .header h1 {{ font-size: 24px; margin-bottom: 5px; }}
        .header .badge {{ background: rgba(255,255,255,0.2); padding: 3px 12px; border-radius: 12px; font-size: 12px; }}
        .header .stats {{ margin-top: 10px; font-size: 14px; opacity: 0.9; }}
        .container {{ max-width: 900px; margin: 20px auto; padding: 0 20px; }}
        .card {{ background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); padding: 25px; margin-bottom: 20px; }}
        .card h2 {{ color: #667eea; margin-bottom: 15px; font-size: 18px; }}
        .form-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
        .form-group {{ display: flex; flex-direction: column; }}
        .form-group.full {{ grid-column: 1 / -1; }}
        label {{ font-size: 13px; color: #666; margin-bottom: 4px; font-weight: 500; }}
        input, textarea {{ padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; transition: border-color 0.2s; }}
        input:focus, textarea:focus {{ outline: none; border-color: #667eea; }}
        textarea {{ resize: vertical; min-height: 60px; }}
        .btn {{ padding: 10px 24px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: transform 0.1s; }}
        .btn:hover {{ transform: translateY(-1px); }}
        .btn:active {{ transform: translateY(0); }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #667eea; color: white; padding: 12px; text-align: left; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #eee; font-size: 14px; }}
        tr:hover {{ background: #f8f9ff; }}
        .empty {{ text-align: center; padding: 40px; color: #999; }}
        .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{app_name} <span class="badge">{env}</span></h1>
        <div class="stats">{total_persons} personas registradas | Views: {page_views}</div>
    </div>
    <div class="container">
        <div class="card">
            <h2>Registrar Nueva Persona</h2>
            <form method="POST" action="/persons">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Nombre *</label>
                        <input name="first_name" placeholder="Juan" required>
                    </div>
                    <div class="form-group">
                        <label>Apellido *</label>
                        <input name="last_name" placeholder="Perez" required>
                    </div>
                    <div class="form-group">
                        <label>Email</label>
                        <input name="email" type="email" placeholder="juan@ejemplo.com">
                    </div>
                    <div class="form-group">
                        <label>Telefono</label>
                        <input name="phone" placeholder="+593 99 123 4567">
                    </div>
                    <div class="form-group">
                        <label>Edad</label>
                        <input name="age" type="number" min="1" max="150" placeholder="30">
                    </div>
                    <div class="form-group">
                        <label>Ciudad</label>
                        <input name="city" placeholder="Quito">
                    </div>
                    <div class="form-group full">
                        <label>Notas</label>
                        <textarea name="notes" placeholder="Observaciones opcionales..."></textarea>
                    </div>
                </div>
                <br>
                <button type="submit" class="btn">Guardar Persona</button>
            </form>
        </div>
        <div class="card">
            <h2>Personas Registradas</h2>
            {table_content}
        </div>
    </div>
    <div class="footer">
        Deployed by devops-agents platform | {app_name} v1.0 | {env}
    </div>
</body>
</html>"""


def _escape_html(text: str) -> str:
    """Escape HTML special characters to prevent XSS."""
    if not text:
        return ""
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#x27;"))


@app.get("/", response_class=HTMLResponse)
def index():
    """Show registration form and persons list."""
    page_views = 0
    try:
        cache = get_cache()
        if cache:
            page_views = cache.incr("prototype_a:page_views")
    except Exception:
        pass

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM persons ORDER BY created_at DESC LIMIT 100")
        persons = cur.fetchall()
        total = len(persons)
        cur.close()
        conn.close()

        if persons:
            rows = ""
            for p in persons:
                rows += (
                    f"<tr>"
                    f"<td>{p['id']}</td>"
                    f"<td>{_escape_html(p['first_name'])} {_escape_html(p['last_name'])}</td>"
                    f"<td>{_escape_html(p['email'] or '-')}</td>"
                    f"<td>{_escape_html(p['phone'] or '-')}</td>"
                    f"<td>{p['age'] or '-'}</td>"
                    f"<td>{_escape_html(p['city'] or '-')}</td>"
                    f"<td>{p['created_at'].strftime('%Y-%m-%d %H:%M') if p['created_at'] else '-'}</td>"
                    f"</tr>"
                )
            table_content = (
                "<table><tr><th>ID</th><th>Nombre</th><th>Email</th>"
                "<th>Telefono</th><th>Edad</th><th>Ciudad</th><th>Registrado</th></tr>"
                f"{rows}</table>"
            )
        else:
            table_content = '<p class="empty">No hay personas registradas aun.</p>'

        return PAGE_TEMPLATE.format(
            app_name=_escape_html(APP_NAME),
            env=_escape_html(APP_ENV),
            total_persons=total,
            page_views=page_views,
            table_content=table_content,
        )
    except Exception as e:
        return f"<h1>Error</h1><p>{type(e).__name__}: database connection failed</p>", 500


@app.post("/persons")
def add_person(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    age: Optional[int] = Form(None),
    city: str = Form(""),
    notes: str = Form(""),
):
    """Register a new person."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO persons (first_name, last_name, email, phone, age, city, notes) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (first_name.strip(), last_name.strip(), email.strip() or None,
         phone.strip() or None, age, city.strip() or None, notes.strip() or None),
    )
    conn.commit()
    cur.close()
    conn.close()

    # Invalidate cache counter
    try:
        cache = get_cache()
        if cache:
            cache.incr("prototype_a:total_persons")
    except Exception:
        pass

    return RedirectResponse(url="/", status_code=302)


@app.get("/api/persons")
def api_list_persons():
    """JSON API — list all persons."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT id, first_name, last_name, email, phone, age, city FROM persons ORDER BY id DESC")
    persons = [dict(p) for p in cur.fetchall()]
    cur.close()
    conn.close()
    return {"persons": persons, "count": len(persons)}


@app.get("/health")
def health():
    """Health check — verifies database and cache connectivity."""
    result = {"status": "healthy", "app": APP_NAME, "env": APP_ENV}

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        result["database"] = "connected"
    except Exception as e:
        result["database"] = "error"
        result["status"] = "degraded"

    try:
        cache = get_cache()
        if cache:
            cache.ping()
            result["redis"] = "connected"
        else:
            result["redis"] = "not configured"
    except Exception:
        result["redis"] = "error"

    return JSONResponse(result, status_code=200 if result["status"] == "healthy" else 503)
