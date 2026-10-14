"""
Hospital Management System - Flask Web Application & API
Provides full CRUD interfaces, interactive Joins explorer, Cursor execution runner,
Triggers audit inspector, and dynamic SQL console.
"""

import os
import sys
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from src.db import db_mgr
import src.init_db as init_db

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/db/status", methods=["GET", "POST"])
def db_status():
    if request.method == "POST":
        data = request.json or {}
        pwd = data.get("password", "")
        success, msg = config.test_mysql_connection(pwd)
        if success:
            config.MYSQL_PASSWORD = pwd
            db_mgr.mode = "mysql"
            # Attempt to initialize MySQL tables
            init_db.init_mysql(pwd)
            return jsonify({"status": "connected", "mode": "mysql", "message": "Successfully connected and switched to MySQL Server!"})
        else:
            return jsonify({"status": "failed", "mode": db_mgr.mode, "message": f"MySQL connection failed: {msg}"}), 400

    return jsonify({
        "mode": db_mgr.mode,
        "mysql_host": config.MYSQL_HOST,
        "mysql_port": config.MYSQL_PORT,
        "mysql_user": config.MYSQL_USER,
        "database": config.MYSQL_DATABASE
    })

@app.route("/api/stats")
def stats():
    total_patients = db_mgr.execute_query("SELECT COUNT(*) AS count FROM patients")[0]["count"]
    total_doctors = db_mgr.execute_query("SELECT COUNT(*) AS count FROM doctors")[0]["count"]
    active_admissions = db_mgr.execute_query("SELECT COUNT(*) AS count FROM admissions WHERE status = 'Admitted'")[0]["count"]
    total_rooms = db_mgr.execute_query("SELECT COUNT(*) AS count FROM rooms")[0]["count"]
    occupied_rooms = db_mgr.execute_query("SELECT COUNT(*) AS count FROM rooms WHERE status = 'Occupied'")[0]["count"]
    
    rev_res = db_mgr.execute_query("SELECT COALESCE(SUM(total_amount), 0) AS rev FROM bills WHERE payment_status = 'Paid'")
    total_revenue = rev_res[0]["rev"] if rev_res else 0

    return jsonify({
        "total_patients": total_patients,
        "total_doctors": total_doctors,
        "active_admissions": active_admissions,
        "total_rooms": total_rooms,
        "occupied_rooms": occupied_rooms,
        "occupancy_rate": round((occupied_rooms / max(total_rooms, 1)) * 100, 1),
        "total_revenue": total_revenue
    })

# ----------------- PATIENTS -----------------
@app.route("/api/patients", methods=["GET", "POST"])
def patients():
    if request.method == "POST":
        data = request.json
        q = """
        INSERT INTO patients (first_name, last_name, gender, dob, blood_group, phone, emergency_contact, address)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """ if db_mgr.mode == "mysql" else """
        INSERT INTO patients (first_name, last_name, gender, dob, blood_group, phone, emergency_contact, address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data.get("first_name"), data.get("last_name"), data.get("gender"),
            data.get("dob"), data.get("blood_group"), data.get("phone"),
            data.get("emergency_contact"), data.get("address")
        )
        res = db_mgr.execute_query(q, params)
        return jsonify({"success": True, "patient_id": res["last_id"]})

    rows = db_mgr.execute_query("SELECT * FROM patients ORDER BY patient_id DESC")
    return jsonify(rows)

# ----------------- DOCTORS -----------------
@app.route("/api/doctors")
def doctors():
    # Demonstrating Self Join to show Mentor Doctor!
    q = """
    SELECT 
        d.doctor_id,
        d.first_name,
        d.last_name,
        d.specialization,
        d.consultation_fee,
        d.salary,
        d.commission_rate,
        d.phone,
        d.email,
        d.status,
        dept.name AS department_name,
        COALESCE(m.first_name || ' ' || m.last_name, 'Senior Consultant') AS mentor_name
    FROM doctors d
    JOIN departments dept ON d.department_id = dept.department_id
    LEFT JOIN doctors m ON d.mentor_doctor_id = m.doctor_id
    ORDER BY d.doctor_id
    """
    if db_mgr.mode == "mysql":
        q = q.replace("|| ' ' ||", ", ' ', ")
        q = q.replace("COALESCE(m.first_name, ' ', m.last_name", "COALESCE(CONCAT(m.first_name, ' ', m.last_name)")

    rows = db_mgr.execute_query(q)
    return jsonify(rows)

# ----------------- ROOMS & BEDS -----------------
@app.route("/api/rooms")
def rooms():
    q = """
    SELECT 
        r.room_id,
        r.room_number,
        r.room_type,
        r.charge_per_day,
        r.floor_number,
        r.status,
        a.admission_id,
        p.first_name,
        p.last_name,
        a.admission_date
    FROM rooms r
    LEFT JOIN admissions a ON r.room_id = a.room_id AND a.status = 'Admitted'
    LEFT JOIN patients p ON a.patient_id = p.patient_id
    ORDER BY r.floor_number, r.room_number
    """
    rows = db_mgr.execute_query(q)
    return jsonify(rows)

# ----------------- ADMISSIONS -----------------
@app.route("/api/admissions", methods=["GET", "POST"])
def admissions():
    if request.method == "POST":
        data = request.json
        pat_id = data.get("patient_id")
        room_id = data.get("room_id")
        doc_id = data.get("doctor_id")
        diag = data.get("diagnosis", "General Clinical Observation")

        # Atomic check and insert
        rm = db_mgr.execute_query("SELECT status FROM rooms WHERE room_id = " + str(int(room_id)))
        if not rm or rm[0]["status"] != "Available":
            return jsonify({"error": "Selected room is not available"}), 400

        q = """
        INSERT INTO admissions (patient_id, room_id, admitting_doctor_id, admission_date, status, diagnosis)
        VALUES (%s, %s, %s, %s, 'Admitted', %s)
        """ if db_mgr.mode == "mysql" else """
        INSERT INTO admissions (patient_id, room_id, admitting_doctor_id, admission_date, status, diagnosis)
        VALUES (?, ?, ?, ?, 'Admitted', ?)
        """
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        res = db_mgr.execute_query(q, (pat_id, room_id, doc_id, now_str, diag))

        # Manually update room status if not triggered by MySQL engine
        if db_mgr.mode == "sqlite":
            db_mgr.execute_query("UPDATE rooms SET status = 'Occupied' WHERE room_id = " + str(int(room_id)))
            db_mgr.execute_query(
                "INSERT INTO audit_logs (table_name, action_type, record_id, description) VALUES (?, ?, ?, ?)",
                ("admissions", "INSERT", res["last_id"], f"Patient {pat_id} admitted to Room {room_id}. Trigger executed.")
            )

        return jsonify({"success": True, "admission_id": res["last_id"]})

    q = """
    SELECT 
        a.admission_id,
        a.patient_id,
        p.first_name || ' ' || p.last_name AS patient_name,
        p.blood_group,
        r.room_number,
        r.room_type,
        d.first_name || ' ' || d.last_name AS doctor_name,
        a.admission_date,
        a.diagnosis,
        a.status
    FROM admissions a
    JOIN patients p ON a.patient_id = p.patient_id
    JOIN rooms r ON a.room_id = r.room_id
    JOIN doctors d ON a.admitting_doctor_id = d.doctor_id
    ORDER BY a.admission_id DESC
    """
    if db_mgr.mode == "mysql":
        q = q.replace("|| ' ' ||", ", ' ', ").replace("p.first_name, ' ', p.last_name", "CONCAT(p.first_name, ' ', p.last_name)").replace("d.first_name, ' ', d.last_name", "CONCAT(d.first_name, ' ', d.last_name)")

    rows = db_mgr.execute_query(q)
    return jsonify(rows)

@app.route("/api/admissions/<int:adm_id>/discharge", methods=["POST"])
def discharge_admission(adm_id):
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Get room id
    adm = db_mgr.execute_query(f"SELECT room_id FROM admissions WHERE admission_id = {adm_id}")
    if not adm:
        return jsonify({"error": "Admission not found"}), 404
    
    room_id = adm[0]["room_id"]

    if db_mgr.mode == "mysql":
        db_mgr.execute_query(f"UPDATE admissions SET status = 'Discharged', discharge_date = '{now_str}' WHERE admission_id = {adm_id}")
    else:
        db_mgr.execute_query(f"UPDATE admissions SET status = 'Discharged', discharge_date = '{now_str}' WHERE admission_id = {adm_id}")
        db_mgr.execute_query(f"UPDATE rooms SET status = 'Available' WHERE room_id = {room_id}")
        db_mgr.execute_query(
            "INSERT INTO audit_logs (table_name, action_type, record_id, description) VALUES (?, ?, ?, ?)",
            ("admissions", "UPDATE", adm_id, f"Patient discharged from Room {room_id}. Bed freed by Trigger.")
        )

    return jsonify({"success": True, "message": "Patient discharged successfully and bed released!"})

# ----------------- APPOINTMENTS -----------------
@app.route("/api/appointments", methods=["GET", "POST"])
def appointments():
    if request.method == "POST":
        data = request.json
        pat_id = data.get("patient_id")
        doc_id = data.get("doctor_id")
        dt = data.get("appointment_date")
        symptoms = data.get("symptoms", "")

        q = """
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, symptoms)
        VALUES (%s, %s, %s, 'Scheduled', %s)
        """ if db_mgr.mode == "mysql" else """
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, symptoms)
        VALUES (?, ?, ?, 'Scheduled', ?)
        """
        res = db_mgr.execute_query(q, (pat_id, doc_id, dt, symptoms))
        return jsonify({"success": True, "appointment_id": res["last_id"]})

    q = """
    SELECT 
        app.appointment_id,
        app.appointment_date,
        app.status,
        app.symptoms,
        p.patient_id,
        p.first_name || ' ' || p.last_name AS patient_name,
        d.doctor_id,
        d.first_name || ' ' || d.last_name AS doctor_name,
        d.specialization
    FROM appointments app
    JOIN patients p ON app.patient_id = p.patient_id
    JOIN doctors d ON app.doctor_id = d.doctor_id
    ORDER BY app.appointment_date DESC
    """
    if db_mgr.mode == "mysql":
        q = q.replace("|| ' ' ||", ", ' ', ").replace("p.first_name, ' ', p.last_name", "CONCAT(p.first_name, ' ', p.last_name)").replace("d.first_name, ' ', d.last_name", "CONCAT(d.first_name, ' ', d.last_name)")

    rows = db_mgr.execute_query(q)
    return jsonify(rows)

# ----------------- BILLING -----------------
@app.route("/api/billing")
def billing():
    q = """
    SELECT 
        b.bill_id,
        b.patient_id,
        p.first_name || ' ' || p.last_name AS patient_name,
        b.room_charges,
        b.doctor_charges,
        b.treatment_charges,
        b.medicine_charges,
        b.tax_percent,
        b.total_amount,
        b.payment_status,
        b.bill_date
    FROM bills b
    JOIN patients p ON b.patient_id = p.patient_id
    ORDER BY b.bill_id DESC
    """
    if db_mgr.mode == "mysql":
        q = q.replace("|| ' ' ||", ", ' ', ").replace("p.first_name, ' ', p.last_name", "CONCAT(p.first_name, ' ', p.last_name)")

    rows = db_mgr.execute_query(q)
    return jsonify(rows)

# ----------------- INTERACTIVE JOINS EXPLORER -----------------
@app.route("/api/joins/<join_type>")
def execute_join_demo(join_type):
    join_type = join_type.lower()
    
    queries = {
        "inner": {
            "title": "INNER JOIN (Exact Matches Only)",
            "explanation": "Returns rows when there is a match in both tables. Only admitted patients currently residing in an assigned room with an attending doctor appear.",
            "sql": """
SELECT 
    p.patient_id,
    p.first_name || ' ' || p.last_name AS patient_name,
    p.blood_group,
    r.room_number,
    r.room_type,
    'Dr. ' || d.first_name || ' ' || d.last_name AS attending_doctor,
    a.admission_date,
    a.diagnosis
FROM admissions a
INNER JOIN patients p ON a.patient_id = p.patient_id
INNER JOIN rooms r ON a.room_id = r.room_id
INNER JOIN doctors d ON a.admitting_doctor_id = d.doctor_id
WHERE a.status = 'Admitted'
            """.strip()
        },
        "left": {
            "title": "LEFT OUTER JOIN (All Patients + Matching Appointments)",
            "explanation": "Returns all rows from the Left table (Patients), regardless of whether they have booked an appointment. Patients who haven't booked show NULL appointment values.",
            "sql": """
SELECT 
    p.patient_id,
    p.first_name || ' ' || p.last_name AS patient_name,
    p.phone,
    app.appointment_id,
    COALESCE(app.status, 'Never Visited') AS appointment_status,
    COALESCE(app.appointment_date, 'No Date Scheduled') AS appointment_date
FROM patients p
LEFT JOIN appointments app ON p.patient_id = app.patient_id
ORDER BY p.patient_id
            """.strip()
        },
        "right": {
            "title": "RIGHT OUTER JOIN (All Doctors + Matching Appointments)",
            "explanation": "Returns all rows from the Right table (Doctors), and matched records from Appointments. Doctors without appointments appear with NULL patient/appointment data.",
            "sql": """
SELECT 
    d.doctor_id,
    'Dr. ' || d.first_name || ' ' || d.last_name AS doctor_name,
    d.specialization,
    app.appointment_id,
    COALESCE(app.status, 'No Appointments') AS appointment_status,
    COALESCE(app.appointment_date, 'N/A') AS appointment_date
FROM appointments app
RIGHT JOIN doctors d ON app.doctor_id = d.doctor_id
ORDER BY d.doctor_id
            """.strip()
        },
        "full": {
            "title": "FULL OUTER JOIN (All Patients UNION All Doctors)",
            "explanation": "Returns all matched and unmatched records from both tables. Implemented in MySQL/SQLite using LEFT JOIN UNION RIGHT JOIN.",
            "sql": """
SELECT 
    p.patient_id,
    p.first_name || ' ' || p.last_name AS patient_name,
    app.appointment_id,
    COALESCE('Dr. ' || d.last_name, 'No Doctor') AS doctor_name,
    COALESCE(app.status, 'Not Booked') AS status
FROM patients p
LEFT JOIN appointments app ON p.patient_id = app.patient_id
LEFT JOIN doctors d ON app.doctor_id = d.doctor_id

UNION

SELECT 
    p.patient_id,
    p.first_name || ' ' || p.last_name AS patient_name,
    app.appointment_id,
    COALESCE('Dr. ' || d.last_name, 'No Doctor') AS doctor_name,
    COALESCE(app.status, 'No Appointment') AS status
FROM appointments app
LEFT JOIN doctors d ON app.doctor_id = d.doctor_id
LEFT JOIN patients p ON app.patient_id = p.patient_id
            """.strip()
        },
        "cross": {
            "title": "CROSS JOIN (Cartesian Product)",
            "explanation": "Produces all possible combinations between Department and Room Types (N × M). Used in hospital capacity and rate card planning.",
            "sql": """
SELECT 
    dept.name AS department_name,
    dept.building_block,
    rt.room_type,
    rt.charge_per_day
FROM departments dept
CROSS JOIN (
    SELECT DISTINCT room_type, charge_per_day FROM rooms
) rt
ORDER BY dept.name, rt.room_type
            """.strip()
        },
        "self": {
            "title": "SELF JOIN (Mentorship & Reporting Hierarchy)",
            "explanation": "Joins the Doctors table to itself via mentor_doctor_id = doctor_id to display the junior doctor and supervising senior mentor hierarchy.",
            "sql": """
SELECT 
    doc.doctor_id AS junior_doctor_id,
    'Dr. ' || doc.first_name || ' ' || doc.last_name AS junior_doctor,
    doc.specialization AS junior_specialization,
    COALESCE('Dr. ' || mentor.first_name || ' ' || mentor.last_name, 'Senior Consultant (Top)') AS mentor_supervisor,
    COALESCE(mentor.specialization, 'Medical Board') AS mentor_specialization
FROM doctors doc
LEFT JOIN doctors mentor ON doc.mentor_doctor_id = mentor.doctor_id
ORDER BY mentor.doctor_id, doc.doctor_id
            """.strip()
        }
    }

    if join_type not in queries:
        return jsonify({"error": "Unknown join type"}), 404

    target = queries[join_type]
    raw_sql = target["sql"]
    
    # Adjust concat for MySQL if needed
    exec_sql = raw_sql
    if db_mgr.mode == "mysql":
        if join_type == "right":
            # Native MySQL RIGHT JOIN syntax
            exec_sql = """
            SELECT 
                d.doctor_id,
                CONCAT('Dr. ', d.first_name, ' ', d.last_name) AS doctor_name,
                d.specialization,
                app.appointment_id,
                COALESCE(app.status, 'No Appointments') AS appointment_status,
                COALESCE(app.appointment_date, 'N/A') AS appointment_date
            FROM appointments app
            RIGHT JOIN doctors d ON app.doctor_id = d.doctor_id
            ORDER BY d.doctor_id
            """
        else:
            exec_sql = exec_sql.replace("|| ' ' ||", ", ' ', ").replace("p.first_name, ' ', p.last_name", "CONCAT(p.first_name, ' ', p.last_name)").replace("d.first_name, ' ', d.last_name", "CONCAT(d.first_name, ' ', d.last_name)").replace("doc.first_name, ' ', doc.last_name", "CONCAT(doc.first_name, ' ', doc.last_name)").replace("mentor.first_name, ' ', mentor.last_name", "CONCAT(mentor.first_name, ' ', mentor.last_name)").replace("'Dr. ' ||", "CONCAT('Dr. ', ")

    start = time.time()
    try:
        rows = db_mgr.execute_query(exec_sql)
        elapsed = round((time.time() - start) * 1000, 2)
        columns = list(rows[0].keys()) if rows else []
        return jsonify({
            "join_type": join_type,
            "title": target["title"],
            "explanation": target["explanation"],
            "sql": raw_sql,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "execution_ms": elapsed
        })
    except Exception as e:
        return jsonify({"error": str(e), "sql": exec_sql}), 500

# ----------------- CURSOR EXECUTION RUNNER -----------------
@app.route("/api/cursor/run", methods=["POST"])
def run_cursor():
    data = request.json or {}
    month_year = data.get("month_year", "2026-10")
    
    trace_logs = [
        f"[CURSOR DECLARE] DECLARE cur_doctors CURSOR FOR SELECT doctor_id, salary, commission_rate FROM doctors WHERE status = 'Active'",
        f"[CURSOR HANDLER] DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE",
        f"[CURSOR OPEN] Opening cur_doctors cursor into memory..."
    ]

    if db_mgr.mode == "mysql":
        try:
            db_mgr.execute_query(f"CALL sp_calculate_monthly_doctor_payouts('{month_year}')")
            trace_logs.append(f"[STORED PROCEDURE] Executed MySQL stored procedure sp_calculate_monthly_doctor_payouts('{month_year}')")
        except Exception as e:
            trace_logs.append(f"[MYSQL NOTICE] Falling back to procedural cursor runner: {e}")

    # Fetch active doctors to simulate/demonstrate cursor fetch steps
    doctors = db_mgr.execute_query("SELECT doctor_id, first_name, last_name, salary, commission_rate, consultation_fee FROM doctors WHERE status = 'Active'")
    
    for doc in doctors:
        doc_id = doc["doctor_id"]
        name = f"Dr. {doc['first_name']} {doc['last_name']}"
        sal = float(doc["salary"])
        comm_rate = float(doc["commission_rate"])
        fee = float(doc["consultation_fee"])

        app_q = f"SELECT COUNT(*) AS cnt FROM appointments WHERE doctor_id = {doc_id} AND status = 'Completed'"
        app_res = db_mgr.execute_query(app_q)
        cnt = app_res[0]["cnt"] if app_res else 0

        comm_earned = round(cnt * fee * comm_rate, 2)
        gross = round(sal + comm_earned, 2)

        trace_logs.append(
            f"[CURSOR FETCH] Doctor #{doc_id} ({name}): {cnt} completed appointments. Base Salary: INR {sal:,.2f} + Comm: INR {comm_earned:,.2f} -> Gross Payout: INR {gross:,.2f}"
        )

        # Upsert payout
        now_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if db_mgr.mode == "mysql":
            db_mgr.execute_query(f"""
            INSERT INTO doctor_payouts (doctor_id, month_year, total_appointments, base_salary, commission_earned, gross_payout, processed_at)
            VALUES ({doc_id}, '{month_year}', {cnt}, {sal}, {comm_earned}, {gross}, '{now_dt}')
            ON DUPLICATE KEY UPDATE total_appointments = {cnt}, commission_earned = {comm_earned}, gross_payout = {gross}, processed_at = '{now_dt}'
            """)
        else:
            db_mgr.execute_query(f"""
            INSERT INTO doctor_payouts (doctor_id, month_year, total_appointments, base_salary, commission_earned, gross_payout, processed_at)
            VALUES ({doc_id}, '{month_year}', {cnt}, {sal}, {comm_earned}, {gross}, '{now_dt}')
            ON CONFLICT(doctor_id, month_year) DO UPDATE SET 
                total_appointments = {cnt}, commission_earned = {comm_earned}, gross_payout = {gross}, processed_at = '{now_dt}'
            """)

    trace_logs.append("[CURSOR CLOSE] Cursor traversal finished. Memory freed.")

    # Fetch updated payouts
    q = """
    SELECT 
        dp.payout_id,
        d.first_name || ' ' || d.last_name AS doctor_name,
        d.specialization,
        dp.month_year,
        dp.total_appointments,
        dp.base_salary,
        dp.commission_earned,
        dp.gross_payout,
        dp.processed_at
    FROM doctor_payouts dp
    JOIN doctors d ON dp.doctor_id = d.doctor_id
    WHERE dp.month_year = ?
    ORDER BY dp.gross_payout DESC
    """
    if db_mgr.mode == "mysql":
        q = q.replace("|| ' ' ||", ", ' ', ").replace("d.first_name, ' ', d.last_name", "CONCAT(d.first_name, ' ', d.last_name)").replace("?", f"'{month_year}'")
        payouts = db_mgr.execute_query(q)
    else:
        payouts = db_mgr.execute_query(q, (month_year,))

    return jsonify({
        "success": True,
        "month_year": month_year,
        "trace_logs": trace_logs,
        "payouts": payouts
    })

# ----------------- TRIGGERS & AUDIT LOGS -----------------
@app.route("/api/triggers/logs")
def trigger_logs():
    rows = db_mgr.execute_query("SELECT * FROM audit_logs ORDER BY log_id DESC LIMIT 30")
    return jsonify(rows)

# ----------------- RAW SQL CONSOLE -----------------
@app.route("/api/sql/execute", methods=["POST"])
def execute_sql():
    data = request.json or {}
    q = data.get("query", "").strip()

    if not q:
        return jsonify({"error": "Empty query"}), 400

    # Basic safety filter
    low = q.lower()
    if any(forbidden in low for forbidden in ["drop database", "shutdown"]):
        return jsonify({"error": "Destructive database operation not permitted"}), 403

    start = time.time()
    try:
        result = db_mgr.execute_query(q)
        elapsed = round((time.time() - start) * 1000, 2)
        if isinstance(result, list):
            cols = list(result[0].keys()) if result else []
            return jsonify({
                "type": "select",
                "columns": cols,
                "rows": result,
                "row_count": len(result),
                "execution_ms": elapsed
            })
        else:
            return jsonify({
                "type": "dml",
                "affected_rows": result.get("affected_rows", 0),
                "execution_ms": elapsed
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("[*] Starting Hospital Management System on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
