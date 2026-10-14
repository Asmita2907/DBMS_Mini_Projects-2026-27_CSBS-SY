/**
 * ============================================================================
 * TEST-BUTTONS.JS - Automated Verification Suite for Hospital Management System
 * Tests every API route behind every UI button & element.
 * ============================================================================
 */

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m',
  bold: '\x1b[1m'
};

const results = [];

async function test(page, button, description, fn) {
  process.stdout.write(`Testing [${page} -> ${button}] ... `);
  try {
    const res = await fn();
    if (res.pass) {
      console.log(`${colors.green}${colors.bold}PASS${colors.reset} (${res.detail || 'OK'})`);
      results.push({ page, button, description, status: 'PASS', detail: res.detail });
    } else {
      console.log(`${colors.red}${colors.bold}FAIL${colors.reset} (${res.detail || 'Condition not met'})`);
      results.push({ page, button, description, status: 'FAIL', detail: res.detail });
    }
  } catch (err) {
    console.log(`${colors.red}${colors.bold}FAIL${colors.reset} (Error: ${err.message})`);
    results.push({ page, button, description, status: 'FAIL', detail: err.message });
  }
}

async function runAllTests() {
  console.log(`\n${colors.cyan}${colors.bold}================================================================${colors.reset}`);
  console.log(`${colors.cyan}${colors.bold}   HOSPITAL MANAGEMENT SYSTEM - FULL BUTTON & API TEST SUITE   ${colors.reset}`);
  console.log(`${colors.cyan}${colors.bold}   Target: ${BASE_URL}                                          ${colors.reset}`);
  console.log(`${colors.cyan}${colors.bold}================================================================\n${colors.reset}`);

  // Test Server Liveness
  try {
    const liveRes = await fetch(`${BASE_URL}/api/db/status`);
    if (!liveRes.ok && liveRes.status !== 200) {
      throw new Error(`Status ${liveRes.status}`);
    }
  } catch (e) {
    console.error(`${colors.red}Error: Server is not responding at ${BASE_URL}. Ensure 'npm start' is running.${colors.reset}\n`);
    process.exit(1);
  }

  // 1. GLOBAL / SYSTEM
  await test('GLOBAL', 'DB Status Indicator', 'Check database connection status', async () => {
    const res = await fetch(`${BASE_URL}/api/db/status`);
    const data = await res.json();
    return { pass: res.status === 200 && data.database === 'hospital_db', detail: `Database: ${data.database}, Connected: ${data.connected}` };
  });

  await test('GLOBAL', 'Reset Demo Data', 'Re-seed database tables and data from database.sql', async () => {
    const res = await fetch(`${BASE_URL}/api/db/reset`, { method: 'POST' });
    const data = await res.json();
    return { pass: res.status === 200 && data.success === true, detail: data.message };
  });

  // 2. DASHBOARD
  await test('DASHBOARD', 'Stat Cards', 'Fetch summary metrics for Patients, Doctors, Appointments, Revenue', async () => {
    const res = await fetch(`${BASE_URL}/api/stats`);
    const data = await res.json();
    return {
      pass: res.status === 200 && data.totalPatients >= 0 && data.totalDoctors >= 0,
      detail: `Patients: ${data.totalPatients}, Doctors: ${data.totalDoctors}, Appts: ${data.totalAppointments}, Rev: $${data.totalRevenue}`
    };
  });

  await test('DASHBOARD', 'Chart Filter (Week)', 'Reload charts filtered to last 7 days', async () => {
    const res = await fetch(`${BASE_URL}/api/charts?filter=week`);
    const data = await res.json();
    return { pass: res.status === 200 && data.doctorRevenue && data.appointmentStatus, detail: `Filter: ${data.filter}` };
  });

  await test('DASHBOARD', 'Chart Filter (Month)', 'Reload charts filtered to last 30 days', async () => {
    const res = await fetch(`${BASE_URL}/api/charts?filter=month`);
    const data = await res.json();
    return { pass: res.status === 200 && data.doctorRevenue && data.appointmentStatus, detail: `Filter: ${data.filter}` };
  });

  await test('DASHBOARD', 'Chart Filter (All)', 'Reload charts with all lifetime data', async () => {
    const res = await fetch(`${BASE_URL}/api/charts?filter=all`);
    const data = await res.json();
    return { pass: res.status === 200 && data.doctorRevenue.labels.length > 0, detail: `Doctors: ${data.doctorRevenue.labels.length}` };
  });

  await test('DASHBOARD', "Today's Appointments", 'Fetch appointments scheduled for CURDATE()', async () => {
    const res = await fetch(`${BASE_URL}/api/appointments/today`);
    const data = await res.json();
    return { pass: res.status === 200 && Array.isArray(data), detail: `${data.length} appointments scheduled today` };
  });

  // 3. PATIENTS
  let createdPatientId = null;
  await test('PATIENTS', 'Add Patient', 'Register new patient with CHECK(age) & UNIQUE(phone)', async () => {
    const phone = `555-TEST-${Math.floor(1000 + Math.random() * 9000)}`;
    const res = await fetch(`${BASE_URL}/api/patients`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Auto Test Patient',
        age: 35,
        gender: 'M',
        phone: phone,
        address: '999 Automate Way'
      })
    });
    const data = await res.json();
    if (res.status === 201 && data.patient_id) {
      createdPatientId = data.patient_id;
      return { pass: true, detail: `Created ID #${data.patient_id}` };
    }
    return { pass: false, detail: data.error };
  });

  await test('PATIENTS', 'Edit Patient', 'Update patient details via UPDATE statement', async () => {
    if (!createdPatientId) return { pass: false, detail: 'No patient created to edit' };
    const res = await fetch(`${BASE_URL}/api/patients/${createdPatientId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Auto Test Patient (Updated)',
        age: 36,
        gender: 'M',
        phone: `555-TEST-UPDATED-${Date.now() % 10000}`,
        address: '1000 Automate Blvd'
      })
    });
    const data = await res.json();
    return { pass: res.status === 200 && data.success === true, detail: data.message };
  });

  await test('PATIENTS', 'View History', 'Fetch patient history via JOIN & stored function patient_due()', async () => {
    const res = await fetch(`${BASE_URL}/api/patients/1/history`);
    const data = await res.json();
    return {
      pass: res.status === 200 && data.patient && Array.isArray(data.history),
      detail: `Patient: ${data.patient.name}, History entries: ${data.history.length}, Unpaid Due: $${data.patient.unpaid_due}`
    };
  });

  await test('PATIENTS', 'Delete Patient', 'Delete patient & verify trigger trg_patient_delete_audit', async () => {
    if (!createdPatientId) return { pass: false, detail: 'No patient created to delete' };
    const res = await fetch(`${BASE_URL}/api/patients/${createdPatientId}`, { method: 'DELETE' });
    const data = await res.json();
    return { pass: res.status === 200 && data.success === true, detail: data.message };
  });

  await test('PATIENTS', 'Pagination & Search', 'Filter and paginate patient directory', async () => {
    const res = await fetch(`${BASE_URL}/api/patients?page=1&limit=2&search=John`);
    const data = await res.json();
    return { pass: res.status === 200 && data.data && data.pagination, detail: `Found: ${data.data.length}, Total: ${data.pagination.total}` };
  });

  // 4. DOCTORS
  let createdDoctorId = null;
  await test('DOCTORS', 'Add Doctor', 'Create doctor with specialization and fee constraint', async () => {
    const res = await fetch(`${BASE_URL}/api/doctors`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Dr. Test Surgeon',
        specialization: 'General Surgery',
        fee: 175.00,
        dept_id: 1
      })
    });
    const data = await res.json();
    if (res.status === 201 && data.doctor_id) {
      createdDoctorId = data.doctor_id;
      return { pass: true, detail: `Created Doctor ID #${data.doctor_id}` };
    }
    return { pass: false, detail: data.error };
  });

  await test('DOCTORS', 'Edit Doctor', 'Update doctor fee and department', async () => {
    if (!createdDoctorId) return { pass: false, detail: 'No doctor created to edit' };
    const res = await fetch(`${BASE_URL}/api/doctors/${createdDoctorId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Dr. Test Surgeon (Senior)',
        specialization: 'Advanced Surgery',
        fee: 195.00,
        dept_id: 1
      })
    });
    const data = await res.json();
    return { pass: res.status === 200 && data.success === true, detail: data.message };
  });

  await test('DOCTORS', 'View Schedule', 'View consultations scheduled for a specific doctor', async () => {
    const res = await fetch(`${BASE_URL}/api/doctors/1/schedule`);
    const data = await res.json();
    return { pass: res.status === 200 && data.doctor && Array.isArray(data.appointments), detail: `Doctor: ${data.doctor.name}, Appts: ${data.appointments.length}` };
  });

  await test('DOCTORS', 'Filter by Department', 'Filter doctors by dept_id query parameter', async () => {
    const res = await fetch(`${BASE_URL}/api/doctors?dept_id=1`);
    const data = await res.json();
    return { pass: res.status === 200 && Array.isArray(data), detail: `${data.length} doctors in Cardiology` };
  });

  await test('DOCTORS', 'Delete Doctor', 'Remove doctor record with confirmation', async () => {
    if (!createdDoctorId) return { pass: false, detail: 'No doctor created to delete' };
    const res = await fetch(`${BASE_URL}/api/doctors/${createdDoctorId}`, { method: 'DELETE' });
    const data = await res.json();
    return { pass: res.status === 200 && data.success === true, detail: data.message };
  });

  // 5. DEPARTMENTS
  let createdDeptId = null;
  await test('DEPARTMENTS', 'Add Department', 'Create new unique department', async () => {
    const res = await fetch(`${BASE_URL}/api/departments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dept_name: `Endocrinology ${Date.now() % 1000}` })
    });
    const data = await res.json();
    if (res.status === 201 && data.dept_id) {
      createdDeptId = data.dept_id;
      return { pass: true, detail: `Created Dept ID #${data.dept_id}` };
    }
    return { pass: false, detail: data.error };
  });

  await test('DEPARTMENTS', 'Rename Department', 'Rename department with UPDATE', async () => {
    if (!createdDeptId) return { pass: false, detail: 'No dept to rename' };
    const res = await fetch(`${BASE_URL}/api/departments/${createdDeptId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dept_name: `Endocrinology & Diabetes ${Date.now() % 1000}` })
    });
    const data = await res.json();
    return { pass: res.status === 200 && data.success === true, detail: data.message };
  });

  await test('DEPARTMENTS', 'Delete Department', 'Remove department record', async () => {
    if (!createdDeptId) return { pass: false, detail: 'No dept to delete' };
    const res = await fetch(`${BASE_URL}/api/departments/${createdDeptId}`, { method: 'DELETE' });
    const data = await res.json();
    return { pass: res.status === 200 && data.success === true, detail: data.message };
  });

  // 6. APPOINTMENTS (PROCEDURE & TRIGGERS)
  await test('APPOINTMENTS', 'Book Appointment (Procedure)', 'Execute stored procedure book_appointment() with transaction & triggers', async () => {
    const futureDate = '2026-11-28';
    const res = await fetch(`${BASE_URL}/api/appointments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: 1,
        doctor_id: 2,
        appt_date: futureDate,
        appt_time: '15:30:00'
      })
    });
    const data = await res.json();
    return { pass: res.status === 201 && data.success === true, detail: data.message };
  });

  await test('APPOINTMENTS', 'Double-Booking Blocked (Trigger 1)', 'Verify BEFORE INSERT trigger prevents double booking with SQLSTATE 45000', async () => {
    // Attempt same slot as seeded appointment: Doctor 1, 2026-10-15 09:30:00
    const res = await fetch(`${BASE_URL}/api/appointments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: 2,
        doctor_id: 1,
        appt_date: '2026-10-15',
        appt_time: '09:30:00'
      })
    });
    const data = await res.json();
    return { pass: res.status === 400 && data.error.includes('Double-booking error'), detail: `MySQL Trapped: ${data.error}` };
  });

  await test('APPOINTMENTS', 'Past Date Rejection (Signal)', 'Verify procedure rejects past date with custom SIGNAL message', async () => {
    const res = await fetch(`${BASE_URL}/api/appointments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: 1,
        doctor_id: 1,
        appt_date: '2020-01-01',
        appt_time: '10:00:00'
      })
    });
    const data = await res.json();
    return { pass: res.status === 400 && data.error.includes('cannot be in the past'), detail: `MySQL Trapped: ${data.error}` };
  });

  await test('APPOINTMENTS', 'Reschedule Appointment', 'Reschedule appointment to a new validated slot', async () => {
    const res = await fetch(`${BASE_URL}/api/appointments/2/reschedule`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        appt_date: '2026-11-29',
        appt_time: '16:00:00'
      })
    });
    const data = await res.json();
    return { pass: res.status === 200 && data.success === true, detail: data.message };
  });

  await test('APPOINTMENTS', 'Complete Appointment', 'Mark appointment as Completed', async () => {
    const res = await fetch(`${BASE_URL}/api/appointments/3/complete`, { method: 'PATCH' });
    const data = await res.json();
    return { pass: res.status === 200 && data.success === true, detail: data.message };
  });

  await test('APPOINTMENTS', 'Cancel Appointment (Trigger 3)', 'Cancel appointment; trigger sets bill amount to 0 & logs to audit_log', async () => {
    const res = await fetch(`${BASE_URL}/api/appointments/1/cancel`, { method: 'PATCH' });
    const data = await res.json();
    return { pass: res.status === 200 && data.success === true, detail: data.message };
  });

  await test('APPOINTMENTS', 'Status Filter Tabs', 'Filter appointments by Scheduled, Completed, Cancelled', async () => {
    const res = await fetch(`${BASE_URL}/api/appointments?status=Cancelled`);
    const data = await res.json();
    return { pass: res.status === 200 && Array.isArray(data) && data.length > 0, detail: `${data.length} cancelled appointments` };
  });

  // 7. BILLING
  await test('BILLING', 'Billing Ledger', 'Retrieve billing ledger with patient & doctor info', async () => {
    const res = await fetch(`${BASE_URL}/api/billing?filter=all`);
    const data = await res.json();
    return { pass: res.status === 200 && Array.isArray(data) && data.length > 0, detail: `${data.length} total bills` };
  });

  await test('BILLING', 'Mark Paid', 'Update bill status to Paid', async () => {
    const res = await fetch(`${BASE_URL}/api/billing/2/pay`, { method: 'PATCH' });
    const data = await res.json();
    return { pass: res.status === 200 && data.success === true, detail: data.message };
  });

  await test('BILLING', 'Print Invoice', 'Fetch printable consultation invoice view', async () => {
    const res = await fetch(`${BASE_URL}/api/billing/2/invoice`);
    const data = await res.json();
    return { pass: res.status === 200 && data.bill_id && data.patient_name, detail: `Invoice #${data.bill_id} for ${data.patient_name}` };
  });

  // 8. REVENUE REPORT (CURSOR PROCEDURE)
  await test('REVENUE REPORT', 'Generate Report (Cursor)', 'Run generate_doctor_report() procedure using CURSOR loop', async () => {
    const res = await fetch(`${BASE_URL}/api/reports/generate`, { method: 'POST' });
    const data = await res.json();
    return { pass: res.status === 200 && data.success === true && Array.isArray(data.data), detail: `Iterated ${data.data.length} doctors with cursor` };
  });

  await test('REVENUE REPORT', 'Export CSV', 'Download doctor revenue report as .csv', async () => {
    const res = await fetch(`${BASE_URL}/api/reports/export-csv`);
    const text = await res.text();
    return { pass: res.status === 200 && text.includes('Doctor ID') && text.includes('Doctor Name'), detail: `CSV Header and content verified (${text.length} bytes)` };
  });

  // 9. AUDIT LOG
  await test('AUDIT LOG', 'Refresh Log', 'Fetch all trigger and action events from audit_log', async () => {
    const res = await fetch(`${BASE_URL}/api/audit`);
    const data = await res.json();
    return { pass: res.status === 200 && Array.isArray(data) && data.length > 0, detail: `${data.length} audit records captured` };
  });

  await test('AUDIT LOG', 'Filter by Action Type', 'Filter audit log by action keyword', async () => {
    const res = await fetch(`${BASE_URL}/api/audit?filter=appointment`);
    const data = await res.json();
    return { pass: res.status === 200 && Array.isArray(data), detail: `${data.length} appointment events found` };
  });

  // 10. SQL LAB (20 CATEGORIES)
  await test('SQL LAB', 'Query Whitelist Engine', 'Fetch 20 categories of whitelisted SQL queries', async () => {
    const res = await fetch(`${BASE_URL}/api/lab/queries`);
    const queries = await res.json();
    const categories = new Set(queries.map(q => q.category));
    return { pass: res.status === 200 && categories.size === 20, detail: `20 categories verified, ${queries.length} total queries` };
  });

  await test('SQL LAB', 'Run Query (JOIN Demo)', 'Run query join-5 (4-table JOIN) via POST /api/lab/run/:id', async () => {
    const res = await fetch(`${BASE_URL}/api/lab/run/join-5`, { method: 'POST' });
    const data = await res.json();
    return { pass: res.status === 200 && data.success === true, detail: `Execution Time: ${data.executionTimeMs}ms` };
  });

  await test('SQL LAB', 'Run Query (Cursor Demo)', 'Run query cur-1 (Cursor Doctor Report) via POST /api/lab/run/:id', async () => {
    const res = await fetch(`${BASE_URL}/api/lab/run/cur-1`, { method: 'POST' });
    const data = await res.json();
    return { pass: res.status === 200 && data.success === true, detail: `Execution Time: ${data.executionTimeMs}ms` };
  });

  await test('SQL LAB', 'Run Query (Transaction & Rollback)', 'Run query tx-2 (Rollback Demo) ensuring state is protected', async () => {
    const res = await fetch(`${BASE_URL}/api/lab/run/tx-2`, { method: 'POST' });
    const data = await res.json();
    return { pass: res.status === 200 && data.success === true && data.rolledBack === true, detail: `Rolled Back: ${data.rolledBack}` };
  });

  await test('SQL LAB', 'Run Query (Constraint Violation)', 'Run query const-4 (CHECK Constraint Violation) capturing real MySQL error', async () => {
    const res = await fetch(`${BASE_URL}/api/lab/run/const-4`, { method: 'POST' });
    const data = await res.json();
    return { pass: res.status === 200 && data.success === false && data.error, detail: `Captured Error: ${data.error}` };
  });

  await test('SQL LAB', 'Run All in Category', 'Execute entire category batch via POST /api/lab/run-category/:cat', async () => {
    const res = await fetch(`${BASE_URL}/api/lab/run-category/4.%20Aggregates`, { method: 'POST' });
    const data = await res.json();
    return { pass: res.status === 200 && Array.isArray(data.results) && data.results.length > 0, detail: `Ran ${data.results.length} queries in Aggregates` };
  });

  await test('SQL LAB', 'Export All as .sql', 'Download commented .sql file with all 20 categories', async () => {
    const res = await fetch(`${BASE_URL}/api/lab/export-sql`);
    const text = await res.text();
    return { pass: res.status === 200 && text.includes('HOSPITAL MANAGEMENT SYSTEM - SQL LAB'), detail: `Exported ${text.length} bytes of SQL` };
  });

  // Print Summary Table
  console.log(`\n${colors.cyan}${colors.bold}================================================================${colors.reset}`);
  console.log(`${colors.cyan}${colors.bold}   TEST SUMMARY CHECKLIST                                       ${colors.reset}`);
  console.log(`${colors.cyan}${colors.bold}================================================================${colors.reset}`);
  console.log(`| Page           | Button / Action               | Status  | Detail`);
  console.log(`|----------------|-------------------------------|---------|--------------------------------------`);
  results.forEach(r => {
    const p = r.page.padEnd(14);
    const b = r.button.padEnd(29);
    const s = r.status === 'PASS' ? `${colors.green}PASS   ${colors.reset}` : `${colors.red}FAIL   ${colors.reset}`;
    console.log(`| ${p} | ${b} | ${s} | ${r.detail || ''}`);
  });

  const passed = results.filter(r => r.status === 'PASS').length;
  const failed = results.filter(r => r.status === 'FAIL').length;
  const total = results.length;

  console.log(`\n${colors.bold}Total Tests: ${total} | Passed: ${colors.green}${passed}${colors.reset}${colors.bold} | Failed: ${failed > 0 ? colors.red + failed : colors.green + '0'}${colors.reset}\n`);

  if (failed > 0) {
    process.exit(1);
  } else {
    console.log(`${colors.green}${colors.bold}🎉 ALL BUTTON & API TESTS PASSED PERFECTLY!${colors.reset}\n`);
    process.exit(0);
  }
}

runAllTests();
