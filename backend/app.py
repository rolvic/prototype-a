"""Prototype A — Backend API (FastAPI + PostgreSQL + Redis)."""
import os
import logging

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import psycopg2
import redis as redis_lib

app = FastAPI(title="Prototype A Backend")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
REDIS_URL = os.environ.get("REDIS_URL", "")


def get_db():
    return psycopg2.connect(DATABASE_URL)


def get_redis():
    if REDIS_URL:
        return redis_lib.from_url(REDIS_URL, decode_responses=True)
    return None


def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS persons (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100),
                age INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database init failed: {e}")


if DATABASE_URL:
    init_db()


HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>Prototype A - Registro de Personas</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; }}
        h1 {{ color: #2c3e50; }}
        form {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
        input {{ padding: 8px 12px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }}
        button {{ padding: 8px 20px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; }}
        button:hover {{ background: #2980b9; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #3498db; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .badge {{ background: #27ae60; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; }}
        .info {{ color: #7f8c8d; font-size: 14px; }}
        .redis {{ color: #e74c3c; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>Prototype A <span class="badge">TEST</span></h1>
    <p class="info">FastAPI + PostgreSQL + Redis | Deployed by devops-agents</p>
    <p class="redis">Page views: {views} (tracked by Redis)</p>
    <form method="POST" action="/persons">
        <h3>Registrar Persona</h3>
        <input name="name" placeholder="Nombre completo" required>
        <input name="email" placeholder="Email" type="email">
        <input name="age" placeholder="Edad" type="number" min="0" max="150">
        <button type="submit">Guardar</button>
    </form>
    <h2>Personas registradas ({count})</h2>
    <table>
        <tr><th>ID</th><th>Nombre</th><th>Email</th><th>Edad</th><th>Registrado</th></tr>
        {rows}
    </table>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    views = 0
    try:
        r = get_redis()
        if r:
            views = r.incr("page_views")
    except Exception:
        pass

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, age, created_at FROM persons ORDER BY id DESC")
        persons = cur.fetchall()
        cur.close()
        conn.close()
        rows = "".join(
            f"<tr><td>{p[0]}</td><td>{p[1]}</td><td>{p[2] or '-'}</td>"
            f"<td>{p[3] or '-'}</td><td>{p[4].strftime('%Y-%m-%d %H:%M') if p[4] else '-'}</td></tr>"
            for p in persons
        )
        return HTML_TEMPLATE.format(rows=rows, count=len(persons), views=views)
    except Exception as e:
        return f"<h1>Error</h1><p>{e}</p>"


@app.post("/persons")
def add_person(name: str = Form(...), email: str = Form(""), age: int = Form(None)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO persons (name, email, age) VALUES (%s, %s, %s)", (name, email or None, age))
    conn.commit()
    cur.close()
    conn.close()

    try:
        r = get_redis()
        if r:
            r.incr("total_persons")
    except Exception:
        pass

    return RedirectResponse(url="/", status_code=302)


@app.get("/api/persons")
def api_persons():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, age FROM persons ORDER BY id DESC")
    persons = [{"id": p[0], "name": p[1], "email": p[2], "age": p[3]} for p in cur.fetchall()]
    cur.close()
    conn.close()
    return {"persons": persons, "count": len(persons)}


@app.get("/health")
def health():
    result = {"status": "healthy"}
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        result["database"] = "connected"
    except Exception as e:
        result["database"] = f"error: {e}"
        result["status"] = "degraded"

    try:
        r = get_redis()
        if r:
            r.ping()
            result["redis"] = "connected"
        else:
            result["redis"] = "not configured"
    except Exception as e:
        result["redis"] = f"error: {e}"
        result["status"] = "degraded"

    status_code = 200 if result["status"] == "healthy" else 503
    return JSONResponse(result, status_code=status_code)
