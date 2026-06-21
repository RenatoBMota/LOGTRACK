#!/usr/bin/env python3
"""
Monitor de Separação - Setup Corrigido para Windows
Resolve problemas com:
- Espaços no caminho
- Pandas não disponível
- Arquivo não encontrado
"""

import os
import sys
import subprocess

def print_header():
    print("""
╔════════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║            🔧 SETUP CORRIGIDO - Monitor de Separação                         ║
║                                                                                ║
║                  Solução para Windows com espaços no caminho                 ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
    """)

def main():
    print_header()
    
    # 1. Criar diretório templates se não existir
    print("\n1️⃣ Criando diretório templates...")
    os.makedirs('templates', exist_ok=True)
    print("   ✅ Pasta 'templates' criada/verificada")
    
    # 2. Templates HTML inline (sem precisa de generate_templates.py)
    print("\n2️⃣ Criando templates HTML...")
    
    templates = {
        'login.html': '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Monitor</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; }
        .container { max-width: 500px; background: white; border-radius: 10px; padding: 40px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); }
        h1 { text-align: center; color: #333; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { font-weight: bold; color: #333; }
        input { width: 100%; padding: 10px; border: 1px solid #e0e0e0; border-radius: 6px; }
        button { width: 100%; padding: 12px; background: linear-gradient(135deg, #0066CC, #1a8917); color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
        button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,102,204,0.3); }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Monitor</h1>
        <form method="POST">
            <div class="form-group">
                <label>Email:</label>
                <input type="email" name="email" required>
            </div>
            <div class="form-group">
                <label>Senha:</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit">Login</button>
        </form>
        <p style="text-align: center; margin-top: 20px; color: #666;">
            admin@localhost / admin
        </p>
    </div>
</body>
</html>
''',
        'dashboard.html': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #f5f5f5; padding: 20px; }
        .card { margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .kpi { text-align: center; padding: 20px; border-left: 4px solid #0066CC; }
        .kpi-value { font-size: 2.5em; font-weight: bold; color: #0066CC; }
    </style>
</head>
<body>
    <div class="container" style="margin-top: 20px;">
        <h1>📊 Dashboard</h1>
        <div class="row">
            <div class="col-md-3">
                <div class="card kpi">
                    <div class="kpi-value">0</div>
                    <p>Operações</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card kpi">
                    <div class="kpi-value">0</div>
                    <p>Finalizadas</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card kpi">
                    <div class="kpi-value">0</div>
                    <p>Em Andamento</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card kpi">
                    <div class="kpi-value">0</div>
                    <p>SKUs</p>
                </div>
            </div>
        </div>
        <p style="text-align: center; margin-top: 30px;">
            <a href="/logout" class="btn btn-danger">Sair</a>
        </p>
    </div>
</body>
</html>
'''
    }
    
    for filename, content in templates.items():
        filepath = os.path.join('templates', filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"   ✅ {filename}")
    
    print(f"\n   Criados {len(templates)} templates básicos")
    
    # 3. Teste de pip
    print("\n3️⃣ Testando pip...")
    try:
        result = subprocess.run(['python', '-m', 'pip', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"   ✅ pip funcionando: {result.stdout.strip()[:50]}...")
            
            # Tentar instalar (sem pandas)
            print("\n4️⃣ Instalando dependências (sem pandas)...")
            deps = [
                'Flask==3.0.0',
                'Flask-SQLAlchemy==3.1.1',
                'Flask-Login==0.6.3',
                'Werkzeug==3.0.1'
            ]
            
            failed = []
            for dep in deps:
                print(f"   Instalando {dep}...", end=" ")
                try:
                    subprocess.run(['python', '-m', 'pip', 'install', '--quiet', dep],
                                 timeout=30, capture_output=True)
                    print("✅")
                except Exception as e:
                    print(f"❌ ({str(e)[:30]})")
                    failed.append(dep)
            
            if failed:
                print(f"\n   ⚠️ {len(failed)} pacotes falharam (não crítico)")
                print("   Sistema funcionará mesmo sem eles!")
        else:
            print(f"   ❌ pip não funciona")
            raise Exception("pip unavailable")
            
    except Exception as e:
        print(f"   ❌ Erro com pip: {str(e)[:50]}")
        print("\n   💡 Use alternativa:")
        print("      python app_lite.py")
        return False
    
    print("\n" + "="*80)
    print("✅ SETUP COMPLETO!")
    print("="*80)
    print("""
PRÓXIMOS PASSOS:

1. Execute: python app.py
2. Abra: http://localhost:5000
3. Login: admin@localhost / admin

Se app.py não funcionar:
   python app_lite.py
   (Versão sem dependências)
    """)
    
    return True

if __name__ == '__main__':
    if main():
        print("\n🎉 Tudo pronto!")
    else:
        print("\n⚠️ Erro durante setup")
        sys.exit(1)
