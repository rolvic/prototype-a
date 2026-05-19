"""Prototype A — Simple person registry with PostgreSQL."""
import os
import logging

from flask import Flask, request, redirect, jsonify
import psycopg2

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_db():
    return psycopg2.connect(DATABASE_URL)


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


# Initialize DB at import time (gunicorn doesn't run __main__)
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
        table {{ width: 100%%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #3498db; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .badge {{ background: #27ae60; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; }}
        .info {{ color: #7f8c8d; font-size: 14px; }}
    </style>
</head>
<body>
    <h1>Prototype A <span class="badge">TEST</span></h1>
    <p class="info">Deployed by devops-agents platform | PostgreSQL backend</p>
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


@app.route("/")
def index():
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
        return HTML_TEMPLATE.format(rows=rows, count=len(persons))
    except Exception as e:
        return f"<h1>Error</h1><p>{e}</p>", 500


@app.route("/persons", methods=["POST"])
def add_person():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip() or None
    age = request.form.get("age", "").strip()
    age = int(age) if age else None
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO persons (name, email, age) VALUES (%s, %s, %s)", (name, email, age))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")


@app.route("/api/persons")
def api_persons():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, age FROM persons ORDER BY id DESC")
    persons = [{"id": p[0], "name": p[1], "email": p[2], "age": p[3]} for p in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify({"persons": persons, "count": len(persons)})


@app.route("/health")
def health():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return jsonify({"status": "healthy", "database": "connected"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500
