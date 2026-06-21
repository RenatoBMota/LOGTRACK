@echo off
REM Script para instalar dependências sem requirements.txt

echo Instalando Flask...
python.exe -m pip install Flask

echo Instalando Flask-SQLAlchemy...
python.exe -m pip install Flask-SQLAlchemy

echo Instalando Flask-Login...
python.exe -m pip install Flask-Login

echo Instalando Werkzeug...
python.exe -m pip install Werkzeug

echo.
echo ✅ Tudo instalado! Iniciando app...
echo.

python app.py
