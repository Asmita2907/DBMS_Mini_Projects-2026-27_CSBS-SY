# AURA Health — Hospital Management System & DBMS Explorer

A full-stack, enterprise-grade Hospital Management System and interactive SQL Laboratory implementing **all types of joins, cursors, triggers, stored procedures, and MySQL commands**.

---

## Quick Start (Run the Website)

1. Open PowerShell or Command Prompt in this folder:
   ```powershell
   cd "C:\Users\aaris\OneDrive\Desktop\DBMS project"
   ```
2. Start the web application:
   ```powershell
   python app.py
   ```
3. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

*Note: The application includes a self-healing zero-config database mode that works immediately out of the box, as well as one-click connection to your local MySQL 8.0 server via the "MySQL Settings" button in the sidebar.*

---

## DBMS Features Implemented

### 1. All Types of SQL Joins
* **INNER JOIN**: In-patients currently admitted with room allocations and attending doctors.
* **LEFT OUTER JOIN**: All registered patients, including those with zero booked appointments.
* **RIGHT OUTER JOIN**: All specialist doctors, including newly onboarded doctors with zero appointments.
* **FULL OUTER JOIN**: Patients unioned with doctors to audit total clinical touchpoints (`LEFT JOIN UNION RIGHT JOIN`).
* **CROSS JOIN**: Cartesian product between Hospital Departments and Room Categories for capacity planning.
* **SELF JOIN**: Doctors table self-referencing `mentor_doctor_id` to map Junior Doctors to Supervising Senior Consultants.

### 2. MySQL Cursors
* **Stored Procedure**: `sp_calculate_monthly_doctor_payouts(IN p_month_year VARCHAR(7))`
* Uses `DECLARE cur_doctors CURSOR FOR ...`, `OPEN`, `FETCH` loop with `NOT FOUND` handler, row-by-row procedural payroll calculation, and `CLOSE`.
* Can be triggered interactively in real time via the **Cursor Runner** tab on the website!

### 3. Automated Database Triggers
* **`trg_after_admission_insert`**: Automatically marks rooms as `'Occupied'` and records an event in `audit_logs`.
* **`trg_after_admission_discharge`**: Automatically frees the room to `'Available'` upon patient discharge.
* **`trg_before_prescription_item_insert`**: Validates medicine stock in pharmacy, decrements inventory, and prevents negative balances.

### 4. Transactions (TCL)
* Atomically executes patient admission with `START TRANSACTION`, `FOR UPDATE` locking, and `ROLLBACK` on conflict.

---

## Directory Organization

```
DBMS project/
├── app.py                     # Flask Web Server & REST API
├── config.py                  # Database connection configuration & fallbacks
├── requirements.txt           # Python dependencies
├── docs/                      # Complete Academic Documentation
│   ├── All_Joins_Explained.md            # Detailed join theories and examples
│   ├── Cursors_and_Procedures_Guide.md   # MySQL cursor lifecycle guide
│   ├── ER_Diagram_and_Schema_Design.md   # Mermaid ER diagram & 1NF/2NF/3NF/BCNF
│   ├── DBMS_Project_Report.md            # Ready-to-submit project report
│   └── linking_mysql_with_antigravity.md # Antigravity MCP integration guide
├── schema/                    # Raw DDL & DML SQL Files
│   ├── 01_create_tables.sql              # Tables, PKs, FKs, CHECK, UNIQUE, Indexes
│   ├── 02_views.sql                      # Multi-table and self-join views
│   ├── 03_triggers.sql                   # Event triggers & audit logging
│   ├── 04_procedures_cursors.sql         # Cursors, stored procedures & functions
│   └── 05_seed_data.sql                  # Comprehensive sample clinical dataset
├── queries/                   # Standalone Query Files
│   ├── joins_demonstration.sql           # All 6 joins with clinical outputs
│   ├── cursor_demonstration.sql          # Cursor execution scripts
│   ├── transactions_demo.sql             # Commit, rollback & savepoint scripts
│   └── advanced_queries.sql              # Group By, Having, Window Functions
├── src/                       # Backend Core Modules
│   ├── db.py                             # Unified database query manager
│   ├── db_connection.py                  # Standalone connection test
│   └── init_db.py                        # Database migration & bootstrap script
├── templates/
│   └── index.html                        # Web UI with dashboard & DBMS lab
└── static/
    ├── css/style.css                     # Custom healthcare styling
    └── js/app.js                         # Dynamic SPA logic & interactive runner
```
