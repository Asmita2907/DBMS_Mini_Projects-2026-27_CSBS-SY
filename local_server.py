from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import sqlite3, json, os, time
BASE=os.path.dirname(os.path.abspath(__file__)); DB=os.path.join(BASE,'hospital_db.sqlite'); INDEX=os.path.join(BASE,'templates','index.html')

def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def rows(q,p=()):
    with conn() as c: return [dict(x) for x in c.execute(q,p).fetchall()]
def execq(q,p=()):
    with conn() as c:
        cur=c.execute(q,p); c.commit(); return {'affected_rows':cur.rowcount,'last_id':cur.lastrowid}

class H(BaseHTTPRequestHandler):
    def sendj(self,d,status=200):
        b=json.dumps(d,default=str).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        p=urlparse(self.path).path
        try:
            if p=='/':
                b=open(INDEX,'rb').read(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b); return
            if p=='/api/db/status': return self.sendj({'mode':'sqlite','database':'hospital_db','mysql_host':'localhost','mysql_port':3306,'mysql_user':'root'})
            if p=='/api/stats':
                total_patients=rows('SELECT COUNT(*) count FROM patients')[0]['count']; total_doctors=rows('SELECT COUNT(*) count FROM doctors')[0]['count']; active=rows("SELECT COUNT(*) count FROM admissions WHERE status='Admitted'")[0]['count']; total_rooms=rows('SELECT COUNT(*) count FROM rooms')[0]['count']; occ=rows("SELECT COUNT(*) count FROM rooms WHERE status='Occupied'")[0]['count']; rev=rows("SELECT COALESCE(SUM(total_amount),0) rev FROM bills WHERE payment_status='Paid'")[0]['rev']; return self.sendj({'total_patients':total_patients,'total_doctors':total_doctors,'active_admissions':active,'total_rooms':total_rooms,'occupied_rooms':occ,'occupancy_rate':round(occ/max(total_rooms,1)*100,1),'total_revenue':rev})
            if p=='/api/patients': return self.sendj(rows('SELECT * FROM patients ORDER BY patient_id DESC'))
            if p=='/api/doctors':
                q="""SELECT d.doctor_id,d.first_name,d.last_name,d.specialization,d.consultation_fee,d.salary,d.commission_rate,d.phone,d.email,d.status,dept.name department_name,COALESCE(m.first_name||' '||m.last_name,'Senior Consultant') mentor_name FROM doctors d JOIN departments dept ON d.department_id=dept.department_id LEFT JOIN doctors m ON d.mentor_doctor_id=m.doctor_id ORDER BY d.doctor_id"""; return self.sendj(rows(q))
            if p=='/api/rooms': return self.sendj(rows("""SELECT r.room_id,r.room_number,r.room_type,r.charge_per_day,r.floor_number,r.status,a.admission_id,p.first_name,p.last_name,a.admission_date FROM rooms r LEFT JOIN admissions a ON r.room_id=a.room_id AND a.status='Admitted' LEFT JOIN patients p ON a.patient_id=p.patient_id ORDER BY r.floor_number,r.room_number"""))
            if p=='/api/admissions': return self.sendj(rows("""SELECT a.admission_id,a.patient_id,p.first_name||' '||p.last_name patient_name,p.blood_group,r.room_number,r.room_type,d.first_name||' '||d.last_name doctor_name,a.admission_date,a.diagnosis,a.status FROM admissions a JOIN patients p ON a.patient_id=p.patient_id JOIN rooms r ON a.room_id=r.room_id JOIN doctors d ON a.admitting_doctor_id=d.doctor_id ORDER BY a.admission_id DESC"""))
            if p=='/api/appointments': return self.sendj(rows("""SELECT app.appointment_id,app.appointment_date,app.status,app.symptoms,p.patient_id,p.first_name||' '||p.last_name patient_name,d.doctor_id,d.first_name||' '||d.last_name doctor_name,d.specialization FROM appointments app JOIN patients p ON app.patient_id=p.patient_id JOIN doctors d ON app.doctor_id=d.doctor_id ORDER BY app.appointment_date DESC"""))
            if p=='/api/billing': return self.sendj(rows("""SELECT b.bill_id,b.patient_id,p.first_name||' '||p.last_name patient_name,b.room_charges,b.doctor_charges,b.treatment_charges,b.medicine_charges,b.tax_percent,b.total_amount,b.payment_status,b.bill_date FROM bills b JOIN patients p ON b.patient_id=p.patient_id ORDER BY b.bill_id DESC"""))
            if p=='/api/triggers/logs': return self.sendj(rows('SELECT * FROM audit_logs ORDER BY log_id DESC LIMIT 30'))
            if p.startswith('/api/joins/'):
                k=p.split('/')[-1]; qmap={
                'inner':("INNER JOIN","""SELECT p.patient_id,p.first_name||' '||p.last_name patient_name,p.blood_group,r.room_number,r.room_type,'Dr. '||d.first_name||' '||d.last_name attending_doctor,a.admission_date,a.diagnosis FROM admissions a INNER JOIN patients p ON a.patient_id=p.patient_id INNER JOIN rooms r ON a.room_id=r.room_id INNER JOIN doctors d ON a.admitting_doctor_id=d.doctor_id WHERE a.status='Admitted'"""),
                'left':("LEFT OUTER JOIN","""SELECT p.patient_id,p.first_name||' '||p.last_name patient_name,p.phone,app.appointment_id,COALESCE(app.status,'Never Visited') appointment_status,COALESCE(app.appointment_date,'No Date Scheduled') appointment_date FROM patients p LEFT JOIN appointments app ON p.patient_id=app.patient_id ORDER BY p.patient_id"""),
                'right':("RIGHT OUTER JOIN","""SELECT d.doctor_id,'Dr. '||d.first_name||' '||d.last_name doctor_name,d.specialization,app.appointment_id,COALESCE(app.status,'No Appointments') appointment_status,COALESCE(app.appointment_date,'N/A') appointment_date FROM doctors d LEFT JOIN appointments app ON app.doctor_id=d.doctor_id ORDER BY d.doctor_id"""),
                'full':("FULL OUTER JOIN","""SELECT p.patient_id,p.first_name||' '||p.last_name patient_name,app.appointment_id,COALESCE('Dr. '||d.last_name,'No Doctor') doctor_name,COALESCE(app.status,'Not Booked') status FROM patients p LEFT JOIN appointments app ON p.patient_id=app.patient_id LEFT JOIN doctors d ON app.doctor_id=d.doctor_id UNION SELECT p.patient_id,p.first_name||' '||p.last_name patient_name,app.appointment_id,COALESCE('Dr. '||d.last_name,'No Doctor') doctor_name,COALESCE(app.status,'No Appointment') status FROM appointments app LEFT JOIN doctors d ON app.doctor_id=d.doctor_id LEFT JOIN patients p ON app.patient_id=p.patient_id"""),
                'cross':("CROSS JOIN","""SELECT dept.name department_name,dept.building_block,rt.room_type,rt.charge_per_day FROM departments dept CROSS JOIN (SELECT DISTINCT room_type,charge_per_day FROM rooms) rt ORDER BY dept.name,rt.room_type"""),
                'self':("SELF JOIN","""SELECT doc.doctor_id junior_doctor_id,'Dr. '||doc.first_name||' '||doc.last_name junior_doctor,doc.specialization junior_specialization,COALESCE('Dr. '||mentor.first_name||' '||mentor.last_name,'Senior Consultant (Top)') mentor_supervisor,COALESCE(mentor.specialization,'Medical Board') mentor_specialization FROM doctors doc LEFT JOIN doctors mentor ON doc.mentor_doctor_id=mentor.doctor_id ORDER BY mentor.doctor_id,doc.doctor_id""")}
                if k not in qmap:return self.sendj({'error':'Unknown join type'},404)
                t,q=qmap[k]; st=time.time(); rr=rows(q); return self.sendj({'join_type':k,'title':t+' (Interactive Demonstration)','explanation':'Executes the supplied join demonstration against the local SQLite hospital database.','sql':q,'columns':list(rr[0]) if rr else [],'rows':rr,'row_count':len(rr),'execution_ms':round((time.time()-st)*1000,2)})
            if p=='/api/sql/execute': return self.sendj({'error':'Use POST for SQL console'},405)
            return self.sendj({'error':'Not found'},404)
        except Exception as e: return self.sendj({'error':str(e)},500)
    def body(self):
        n=int(self.headers.get('Content-Length','0')); return json.loads(self.rfile.read(n) or '{}')
    def do_POST(self):
        p=urlparse(self.path).path; d=self.body()
        try:
            if p=='/api/patients':
                r=execq('INSERT INTO patients (first_name,last_name,gender,dob,blood_group,phone,emergency_contact,address) VALUES (?,?,?,?,?,?,?,?)',tuple(d.get(k) for k in ['first_name','last_name','gender','dob','blood_group','phone','emergency_contact','address'])); return self.sendj({'success':True,'patient_id':r['last_id']})
            if p=='/api/appointments':
                r=execq("INSERT INTO appointments (patient_id,doctor_id,appointment_date,status,symptoms) VALUES (?,?,?,'Scheduled',?)",(d.get('patient_id'),d.get('doctor_id'),d.get('appointment_date'),d.get('symptoms',''))); return self.sendj({'success':True,'appointment_id':r['last_id']})
            if p=='/api/admissions':
                room=d.get('room_id'); rm=rows('SELECT status FROM rooms WHERE room_id=?',(room,));
                if not rm or rm[0]['status']!='Available': return self.sendj({'error':'Selected room is not available'},400)
                r=execq("INSERT INTO admissions (patient_id,room_id,admitting_doctor_id,admission_date,status,diagnosis) VALUES (?,?,?,datetime('now'),'Admitted',?)",(d.get('patient_id'),room,d.get('doctor_id'),d.get('diagnosis','General Clinical Observation'))); execq("UPDATE rooms SET status='Occupied' WHERE room_id=?",(room,)); execq("INSERT INTO audit_logs(table_name,action_type,record_id,description) VALUES (?,?,?,?)",('admissions','INSERT',r['last_id'],f"Patient {d.get('patient_id')} admitted to Room {room}. Trigger executed.")); return self.sendj({'success':True,'admission_id':r['last_id']})
            if p.startswith('/api/admissions/') and p.endswith('/discharge'):
                aid=int(p.split('/')[3]); a=rows('SELECT room_id FROM admissions WHERE admission_id=?',(aid,));
                if not a:return self.sendj({'error':'Admission not found'},404)
                room=a[0]['room_id']; execq("UPDATE admissions SET status='Discharged',discharge_date=datetime('now') WHERE admission_id=?",(aid,)); execq("UPDATE rooms SET status='Available' WHERE room_id=?",(room,)); execq("INSERT INTO audit_logs(table_name,action_type,record_id,description) VALUES (?,?,?,?)",('admissions','UPDATE',aid,f'Patient discharged from Room {room}. Bed freed by Trigger.')); return self.sendj({'success':True,'message':'Patient discharged successfully and bed released!'})
            if p=='/api/cursor/run':
                m=d.get('month_year','2026-10'); trace=['[CURSOR DECLARE] DECLARE cur_doctors CURSOR FOR active doctors','[CURSOR HANDLER] DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE','[CURSOR OPEN] Opening cur_doctors cursor into memory...']; docs=rows("SELECT doctor_id,first_name,last_name,salary,commission_rate,consultation_fee FROM doctors WHERE status='Active'")
                for x in docs:
                    cnt=rows("SELECT COUNT(*) cnt FROM appointments WHERE doctor_id=? AND status='Completed'",(x['doctor_id'],))[0]['cnt']; comm=round(cnt*float(x['consultation_fee'])*float(x['commission_rate']),2); gross=round(float(x['salary'])+comm,2); trace.append(f"[CURSOR FETCH] Doctor #{x['doctor_id']} (Dr. {x['first_name']} {x['last_name']}): {cnt} completed appointments. Base Salary: INR {float(x['salary']):,.2f} + Comm: INR {comm:,.2f} -> Gross Payout: INR {gross:,.2f}"); execq("INSERT INTO doctor_payouts(doctor_id,month_year,total_appointments,base_salary,commission_earned,gross_payout,processed_at) VALUES(?,?,?,?,?,?,datetime('now')) ON CONFLICT(doctor_id,month_year) DO UPDATE SET total_appointments=excluded.total_appointments,commission_earned=excluded.commission_earned,gross_payout=excluded.gross_payout,processed_at=excluded.processed_at",(x['doctor_id'],m,cnt,x['salary'],comm,gross))
                trace.append('[CURSOR CLOSE] Cursor traversal finished. Memory freed.'); payout=rows("SELECT dp.payout_id,d.first_name||' '||d.last_name doctor_name,d.specialization,dp.month_year,dp.total_appointments,dp.base_salary,dp.commission_earned,dp.gross_payout,dp.processed_at FROM doctor_payouts dp JOIN doctors d ON dp.doctor_id=d.doctor_id WHERE dp.month_year=? ORDER BY dp.gross_payout DESC",(m,)); return self.sendj({'success':True,'month_year':m,'trace_logs':trace,'payouts':payout})
            if p=='/api/sql/execute':
                q=d.get('query','').strip(); low=q.lower()
                if not q:return self.sendj({'error':'Empty query'},400)
                if 'drop database' in low or 'shutdown' in low:return self.sendj({'error':'Destructive database operation not permitted'},403)
                st=time.time(); c=conn(); cur=c.execute(q); c.commit();
                if q.lstrip().lower().startswith(('select','pragma','with','explain')):
                    rr=[dict(x) for x in cur.fetchall()]; return self.sendj({'type':'select','columns':list(rr[0]) if rr else [],'rows':rr,'row_count':len(rr),'execution_ms':round((time.time()-st)*1000,2)})
                return self.sendj({'type':'dml','affected_rows':cur.rowcount,'execution_ms':round((time.time()-st)*1000,2)})
            return self.sendj({'error':'Not found'},404)
        except Exception as e:return self.sendj({'error':str(e)},500)
    def log_message(self,*args): pass

print('AURA Health running at http://localhost:5000')
ThreadingHTTPServer(('0.0.0.0',5000),H).serve_forever()
