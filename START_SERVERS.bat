@echo off
title Tarim Kuraklik Sistemi - Sunucular
color 0A

echo ============================================================
echo    TARIMSAL KURAKLIK TAKIP SISTEMI
echo    Sunucular Baslatiliyor...
echo ============================================================
echo.

:: Frontend sunucusunu arka planda baslat
echo [1/2] Frontend sunucusu baslatiliyor (Port 8080)...
cd /d "%~dp0frontend"
start /B python -m http.server 8080

:: 2 saniye bekle
timeout /t 2 /nobreak > nul

:: Backend sunucusunu baslat
echo [2/2] Backend sunucusu baslatiliyor (Port 5000)...
cd /d "%~dp0backend"
start /B python run.py

:: 3 saniye bekle
timeout /t 3 /nobreak > nul

echo.
echo ============================================================
echo    SUNUCULAR BASLATILDI!
echo ============================================================
echo.
echo    Frontend: http://localhost:8080
echo    Backend:  http://localhost:5000
echo.
echo    Giris Sayfasi: http://localhost:8080/login.html
echo    Kayit Sayfasi: http://localhost:8080/register.html
echo.
echo ============================================================
echo    Bu pencereyi KAPATMAYIN! Sunucular burada calisiyor.
echo    Durdurmak icin CTRL+C basin.
echo ============================================================
echo.

:: Tarayiciyi otomatik ac
start http://localhost:8080/login.html

:: Bekle (pencereyi acik tut)
pause
