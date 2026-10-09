"""Hospital Management System - simple Flask app (patients, doctors, appointments)."""
import json
import logging
import os
import sqlite3
import sys
import tempfile
import time

from flask import Flask, jsonify, render_template_string, request

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER,
  gender TEXT, phone TEXT, disease TEXT);
CREATE TABLE IF NOT EXISTS doctors(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, specialization TEXT);
CREATE TABLE IF NOT EXISTS appointments(
  id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER NOT NULL,
  doctor_id INTEGER NOT NULL, date TEXT NOT NULL, reason TEXT);
"""


class JsonFormatter(logging.Formatter):
    """Structured logs; 'severity' is understood by Google Cloud Logging."""

    def format(self, record):
        return json.dumps({
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        })


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    log = logging.getLogger("hms")
    log.handlers = [handler]
    log.setLevel(logging.INFO)
    log.propagate = False
    return log


log = setup_logging()

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hospital Management System</title>
<style>
body{font-family:system-ui,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#1f2937}
h1{color:#0f766e}section{border:1px solid #d1d5db;border-radius:8px;padding:12px 16px;margin:16px 0}
input,select,button{padding:6px;margin:3px}button{background:#0f766e;color:#fff;border:0;border-radius:4px;cursor:pointer}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #e5e7eb;padding:4px;text-align:left}
</style></head><body>
<h1>Hospital Management System</h1>
<p id="stats"></p>
<section><h3>Add patient</h3>
<input id="pn" placeholder="Name"><input id="pa" type="number" placeholder="Age" style="width:70px">
<select id="pg"><option>Male</option><option>Female</option><option>Other</option></select>
<input id="pp" placeholder="Phone"><input id="pd" placeholder="Condition">
<button onclick="add('patients',{name:pn.value,age:+pa.value,gender:pg.value,phone:pp.value,disease:pd.value})">Add</button>
<table id="patients"></table></section>
<section><h3>Add doctor</h3>
<input id="dn" placeholder="Name"><input id="ds" placeholder="Specialization">
<button onclick="add('doctors',{name:dn.value,specialization:ds.value})">Add</button>
<table id="doctors"></table></section>
<section><h3>Book appointment</h3>
<input id="ap" type="number" placeholder="Patient ID" style="width:100px">
<input id="ad" type="number" placeholder="Doctor ID" style="width:100px">
<input id="at" type="date"><input id="ar" placeholder="Reason">
<button onclick="add('appointments',{patient_id:+ap.value,doctor_id:+ad.value,date:at.value,reason:ar.value})">Book</button>
<table id="appointments"></table></section>
<script>
async function load(t){
  const r=await fetch('/api/'+t);const d=await r.json();
  const el=document.getElementById(t);
  if(!d.length){el.innerHTML='<tr><td>No records</td></tr>';return;}
  const k=Object.keys(d[0]);
  el.innerHTML='<tr>'+k.map(x=>'<th>'+x+'</th>').join('')+'</tr>'+
    d.map(o=>'<tr>'+k.map(x=>'<td>'+(o[x]??'')+'</td>').join('')+'</tr>').join('');
}
async function add(t,body){
  const r=await fetch('/api/'+t,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(!r.ok){alert((await r.json()).error||'Error');}
  refresh();
}
async function refresh(){
  ['patients','doctors','appointments'].forEach(load);
  const s=await (await fetch('/api/stats')).json();
  document.getElementById('stats').textContent=
    `Patients: ${s.patients} | Doctors: ${s.doctors} | Appointments: ${s.appointments}`;
}
refresh();
</script></body></html>"""


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get("DB_PATH") or os.path.join(tempfile.gettempdir(), "hospital.db")

    def db():
        conn = sqlite3.connect(app.config["DB_PATH"])
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        return conn

    def rows(sql, args=()):
        conn = db()
        try:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]
        finally:
            conn.close()

    def insert(sql, args):
        conn = db()
        try:
            cur = conn.execute(sql, args)
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    @app.before_request
    def start_timer():
        request._t = time.time()

    @app.after_request
    def access_log(resp):
        ms = round((time.time() - getattr(request, "_t", time.time())) * 1000, 1)
        if request.path != "/health":
            log.info(f"{request.method} {request.path} -> {resp.status_code} ({ms} ms)")
        return resp

    @app.errorhandler(Exception)
    def on_error(e):
        log.error(f"Unhandled error on {request.path}: {e!r}")
        return jsonify(error="internal server error"), 500

    @app.get("/")
    def home():
        return render_template_string(PAGE)

    @app.get("/health")
    def health():
        """Liveness/readiness: verifies the database is reachable."""
        try:
            rows("SELECT 1 AS ok")
            return jsonify(status="healthy"), 200
        except Exception as e:
            log.error(f"Health check failed: {e!r}")
            return jsonify(status="unhealthy", error=str(e)), 503

    @app.get("/api/patients")
    def list_patients():
        return jsonify(rows("SELECT * FROM patients ORDER BY id"))

    @app.post("/api/patients")
    def add_patient():
        d = request.get_json(silent=True) or {}
        if not d.get("name"):
            return jsonify(error="name is required"), 400
        pid = insert(
            "INSERT INTO patients(name,age,gender,phone,disease) VALUES(?,?,?,?,?)",
            (d["name"], d.get("age"), d.get("gender"), d.get("phone"), d.get("disease")))
        log.info(f"Patient created id={pid}")
        return jsonify(id=pid), 201

    @app.get("/api/doctors")
    def list_doctors():
        return jsonify(rows("SELECT * FROM doctors ORDER BY id"))

    @app.post("/api/doctors")
    def add_doctor():
        d = request.get_json(silent=True) or {}
        if not d.get("name"):
            return jsonify(error="name is required"), 400
        did = insert("INSERT INTO doctors(name,specialization) VALUES(?,?)",
                     (d["name"], d.get("specialization")))
        log.info(f"Doctor created id={did}")
        return jsonify(id=did), 201

    @app.get("/api/appointments")
    def list_appointments():
        return jsonify(rows("""
            SELECT a.id, p.name AS patient, d.name AS doctor, a.date, a.reason
            FROM appointments a
            JOIN patients p ON p.id=a.patient_id
            JOIN doctors d ON d.id=a.doctor_id ORDER BY a.date"""))

    @app.post("/api/appointments")
    def add_appointment():
        d = request.get_json(silent=True) or {}
        if not (d.get("patient_id") and d.get("doctor_id") and d.get("date")):
            return jsonify(error="patient_id, doctor_id and date are required"), 400
        if not rows("SELECT 1 FROM patients WHERE id=?", (d["patient_id"],)):
            return jsonify(error="patient not found"), 404
        if not rows("SELECT 1 FROM doctors WHERE id=?", (d["doctor_id"],)):
            return jsonify(error="doctor not found"), 404
        aid = insert("INSERT INTO appointments(patient_id,doctor_id,date,reason) VALUES(?,?,?,?)",
                     (d["patient_id"], d["doctor_id"], d["date"], d.get("reason")))
        log.info(f"Appointment created id={aid}")
        return jsonify(id=aid), 201

    @app.get("/api/stats")
    def stats():
        return jsonify(
            patients=rows("SELECT COUNT(*) c FROM patients")[0]["c"],
            doctors=rows("SELECT COUNT(*) c FROM doctors")[0]["c"],
            appointments=rows("SELECT COUNT(*) c FROM appointments")[0]["c"])

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))