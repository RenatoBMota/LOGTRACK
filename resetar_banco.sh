#!/bin/bash

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║        🔄 Resetando banco de dados...                        ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Deletar banco antigo
rm -f monitor_separacao.db

# Deletar pasta uploads
rm -rf uploads

echo "✅ Banco e uploads removidos"
echo ""
echo "⏳ Iniciando app (vai recriar tudo)..."
echo ""

python app.py
