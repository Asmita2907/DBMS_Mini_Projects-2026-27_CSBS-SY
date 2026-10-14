@echo off
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -pAarish@8788 < "C:\Users\aaris\OneDrive\Desktop\DBMS project\database.sql"
if %ERRORLEVEL% == 0 (
    echo SUCCESS: hospital_db imported successfully!
) else (
    echo ERROR: Something went wrong. Check MySQL service and password.
)
