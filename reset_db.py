#!/usr/bin/env python3
"""
Script para resetar o banco de dados do LogTrack
Use quando receber erro: "no such column: load_operation.destination"
"""

import os
import sqlite3
from pathlib import Path

def resetar_banco():
    """Resetar banco de dados deletando e deixando criar novo"""
    db_path = 'monitor_separacao.db'
    
    # Verificar se existe
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("✅ Banco de dados antigo deletado com sucesso!")
            print(f"📁 Arquivo removido: {os.path.abspath(db_path)}")
            return True
        except Exception as e:
            print(f"❌ Erro ao deletar banco: {e}")
            return False
    else:
        print(f"ℹ️ Banco de dados não encontrado: {db_path}")
        print("✅ Ele será criado novo quando você executar: python app.py")
        return True

def adicionar_coluna_se_necessario():
    """Tenta adicionar coluna 'destination' ao banco existente (alternativa)"""
    db_path = 'monitor_separacao.db'
    
    if not os.path.exists(db_path):
        print("📌 Banco não existe, será criado novo ao executar app.py")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Tentar adicionar coluna
        cursor.execute('ALTER TABLE load_operation ADD COLUMN destination VARCHAR(200)')
        conn.commit()
        conn.close()
        
        print("✅ Coluna 'destination' adicionada com sucesso ao banco existente!")
        
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e):
            print("ℹ️ Coluna 'destination' já existe no banco de dados")
        else:
            print(f"⚠️ Erro: {e}")
            print("💡 Tente deletar o banco: python reset_db.py --delete")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

def main():
    """Menu principal"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║        🔄 RESETAR BANCO DE DADOS - LogTrack                  ║
║                                                                ║
║   Erro: "no such column: load_operation.destination"         ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    print("Escolha uma opção:\n")
    print("1️⃣  Deletar banco (RECOMENDADO - mais simples)")
    print("2️⃣  Tentar adicionar coluna ao banco existente (mantém dados)")
    print("3️⃣  Cancelar\n")
    
    escolha = input("Digite sua escolha (1, 2 ou 3): ").strip()
    
    if escolha == '1':
        print("\n⚠️  Você está prestes a DELETAR o banco de dados!")
        print("📌 Todos os dados serão perdidos, mas o app recriará tudo novo.\n")
        confirmar = input("Tem certeza? (digite 'SIM' para confirmar): ").strip().upper()
        
        if confirmar == 'SIM':
            if resetar_banco():
                print("\n" + "="*60)
                print("✅ PRONTO! Agora execute:")
                print("   python app.py")
                print("="*60)
                print("\n📝 O banco será recriado automaticamente com:")
                print("   ✅ Todas as tabelas corretas")
                print("   ✅ Coluna 'destination' inclusa")
                print("   ✅ Admin padrão: admin@sistema / admin123")
                print("   ✅ Metas SLA padrão já criadas\n")
        else:
            print("❌ Operação cancelada.")
    
    elif escolha == '2':
        print("\n🔧 Tentando adicionar coluna ao banco existente...\n")
        adicionar_coluna_se_necessario()
        print("\nℹ️  Agora execute: python app.py")
    
    elif escolha == '3':
        print("❌ Cancelado.")
    
    else:
        print("❌ Opção inválida!")

if __name__ == '__main__':
    main()
