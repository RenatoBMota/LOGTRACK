# 🔄 RESETAR BANCO DE DADOS - LogTrack

## ⚠️ O Problema

Você recebeu um erro `OperationalError`:
```
no such column: load_operation.destination
```

Isso acontece porque:
- ✅ O código (app.py) foi atualizado com a coluna `destination`
- ❌ O banco de dados antigo não tem essa coluna ainda

## ✅ A Solução (3 opções)

### **OPÇÃO 1: Deletar o banco e deixar criar novo (Recomendado)**

```bash
# Deletar banco antigo
del monitor_separacao.db

# OU no Linux/Mac:
rm monitor_separacao.db

# Depois execute:
python app.py
```

**O que acontece:**
1. ✅ Banco antigo deletado
2. ✅ app.py cria banco NOVO com todas as colunas corretas
3. ✅ Admin padrão criado automaticamente
4. ✅ Metas SLA padrão criadas
5. ✅ FUNCIONA PERFEITO!

---

### **OPÇÃO 2: Adicionar coluna ao banco existente (Manual)**

Se você quer manter os dados:

```python
import sqlite3

conn = sqlite3.connect('monitor_separacao.db')
cursor = conn.cursor()

# Adicionar coluna destination
cursor.execute('''
    ALTER TABLE load_operation 
    ADD COLUMN destination VARCHAR(200)
''')

conn.commit()
conn.close()
print("✅ Coluna 'destination' adicionada com sucesso!")
```

---

### **OPÇÃO 3: Usar script Python**

Criar arquivo `reset_db.py`:

```python
#!/usr/bin/env python3
import os
import sqlite3

db_path = 'monitor_separacao.db'

# Opção A: Deletar banco (mais fácil)
if os.path.exists(db_path):
    os.remove(db_path)
    print("✅ Banco de dados deletado!")
    print("✅ Execute: python app.py")
    print("✅ Um novo banco será criado automaticamente!")

# Opção B: Adicionar coluna
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('ALTER TABLE load_operation ADD COLUMN destination VARCHAR(200)')
        conn.commit()
        conn.close()
        print("✅ Coluna 'destination' adicionada!")
    except sqlite3.OperationalError as e:
        print(f"⚠️ Coluna pode já existir: {e}")
```

Execute:
```bash
python reset_db.py
```

---

## 🚀 **Passo a Passo Final**

### **Windows:**
1. Abra a pasta do seu projeto
2. Procure o arquivo `monitor_separacao.db`
3. Delete ele
4. Execute: `python app.py`
5. ✅ Novo banco criado!

### **Linux/Mac:**
```bash
cd seu-logtrack/
rm monitor_separacao.db
python app.py
```

---

## 📝 **Credenciais Padrão**

Após resetar, use:
- **Email:** `admin@sistema`
- **Senha:** `admin123`

---

## ✅ **Pronto!**

Depois disso:
- ✅ Campo "Destino" aparece no cadastro de operações
- ✅ "Destino" é salvo no banco
- ✅ "Destino" aparece nos cards de operação
- ✅ TUDO funciona perfeitamente!

---

**Escolha a OPÇÃO 1 (Deletar banco) - é a mais simples!** 🎉
