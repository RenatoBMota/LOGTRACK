@echo off
chcp 65001 > nul
cls

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║        🚀 INSTALAÇÃO DO LOGTRACK - WINDOWS                   ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

echo ⏳ Instalando dependências do LogTrack...
echo.

python -m pip install --upgrade pip
python -m pip install Flask
python -m pip install Flask-SQLAlchemy
python -m pip install Flask-Login
python -m pip install Werkzeug

echo.
echo ✅ Dependências instaladas com sucesso!
echo.
echo 🚀 Iniciando LogTrack na porta 3000...
echo.
echo 📱 Acesse: http://localhost:3000
echo 🔐 Login: admin@sistema / admin123
echo.
echo ⏸️  Pressione CTRL+C para parar o servidor
echo.

python app.py

pause
