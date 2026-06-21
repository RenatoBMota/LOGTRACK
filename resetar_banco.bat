@echo off
REM Script para resetar banco de dados e metas SLA

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║        🔄 Resetando banco de dados...                        ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Deletar banco antigo
del monitor_separacao.db 2>nul

REM Deletar pasta uploads
rmdir /s /q uploads 2>nul

echo ✅ Banco e uploads removidos
echo.
echo ⏳ Iniciando app (vai recriar tudo)...
echo.

python app.py

pause
