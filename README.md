# 🚀 Monitor de Separação - Sistema Completo

**Sistema web profissional para monitoramento de produtividade logística, desenvolvido em Python com Flask.**

---

## ✨ Características

✅ **Autenticação completa** - Login, registro e controle de roles (admin, operator, pending)  
✅ **Gerenciamento de operações** - Criar, iniciar, finalizar e acompanhar carregamentos em tempo real  
✅ **Dashboard de KPIs** - Indicadores de produtividade com gráficos e ranking de colaboradores  
✅ **Cadastros completos** - Separadores, unidades, locais e tipos de ocorrência  
✅ **Relatórios avançados** - Com filtros e exportação em CSV (BOM UTF-8)  
✅ **Monitoramento SLA** - Dashboard dedicado com violações e metas configuráveis  
✅ **Gerenciamento de usuários** - Convite, aprovação e definição de perfis  
✅ **Configurações personalizáveis** - Logo, cores, nome do aplicativo  
✅ **Interface responsiva** - Desktop, tablet e mobile  
✅ **Banco de dados SQLite** - Pronto para uso, sem configuração  

---

## 📦 O que está incluído

```
arquivos-gerados/
├── app.py                      # 🔥 Aplicação Flask principal (650+ linhas)
├── requirements.txt            # Dependências Python
├── generate_templates.py       # Script para gerar templates HTML
├── base_layout.html            # Template base com sidebar
├── login.html                  # Página de login
├── INSTALACAO.md               # Guia detalhado de instalação
├── README.md                   # Este arquivo
│
└── templates/                  # 📄 Templates (gerados)
    ├── login.html
    ├── register.html
    ├── pending_approval.html
    ├── operation.html           # Tela de operações
    ├── dashboard.html           # Dashboard de KPIs
    ├── registrations.html       # Cadastros em abas
    ├── reports.html             # Relatório de operações
    ├── occurrence_report.html   # Relatório de ocorrências
    ├── sla.html                 # Dashboard SLA
    ├── sla_goals.html           # Metas SLA
    ├── users.html               # Gerenciamento de usuários
    └── settings.html            # Configurações do sistema
```

---

## 🚀 Início Rápido (3 minutos)

### 1️⃣ Preparar o ambiente
```bash
# Criar pasta
mkdir monitor-separacao
cd monitor-separacao

# Copiar todos os arquivos para esta pasta
# (app.py, requirements.txt, generate_templates.py, *.html)
```

### 2️⃣ Instalar Python e dependências
```bash
# Criar ambiente virtual
python -m venv venv

# Ativar
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 3️⃣ Gerar templates
```bash
python generate_templates.py
```

### 4️⃣ Executar a aplicação
```bash
python app.py
```

**Pronto!** 🎉 Acesse: **http://localhost:5000**

---

## 🔐 Credenciais Padrão

| Campo | Valor |
|-------|-------|
| **Email** | admin@localhost |
| **Senha** | admin |
| **Perfil** | Administrator (acesso total) |

> ⚠️ **Importante:** Altere a senha após o primeiro login!

---

## 📊 Funcionalidades Principais

### 👥 Autenticação e Controle de Acesso

**3 Roles disponíveis:**
- **Admin** - Acesso total ao sistema
- **Operator** - Operação, relatórios e ocorrências
- **Pending** - Aguardando aprovação do admin

**Fluxo de novos usuários:**
1. Usuário se registra → role `pending` automático
2. Admin aprova em `/users` → muda para `admin` ou `operator`
3. Usuário acessa o sistema

### 📦 Operações

**Página: `/operation`**

Gerenciar ciclo de vida de operações:
- ✏️ **Criar** operação com detalhes (equipe, separadores, tipo, unidade, local, carga, SKUs, peso)
- ▶️ **Iniciar** (carimba data/hora automática)
- ⏹️ **Finalizar** (calcula duração automaticamente)
- 🗑️ **Deletar** operação
- ⚠️ **Registrar ocorrências** (problemas por item)

**Status da operação:**
```
Não Iniciado → Em andamento → Finalizado
```

### 📊 Dashboard

**Página: `/dashboard`** *(admin only)*

Indicadores de performance em tempo real:
- Tempo médio por SKU
- Tempo médio por tonelada
- Tempo médio por carga
- Total de SKUs processados
- Peso total
- Cargas finalizadas
- Total de ocorrências

**Ranking de colaboradores** com métricas detalhadas.

### 📋 Cadastros

**Página: `/registrations`** *(admin only)*

Gerenciar dados mestre:
- **Separadores** - Colaboradores (nome + matrícula)
- **Unidades** - Filiais/Depósitos
- **Locais** - Por unidade (até 100+ por unidade)
- **Tipos de Ocorrência** - Avaria, troca, devolução, etc.

**Ações disponíveis:**
- Adicionar novo registro
- Ativar/desativar clicando no badge
- Deletar registro

### 📄 Relatórios

**Página: `/reports`**

**Relatório de Operações** - Tabela com todas as separações
- Filtros: data, separador, tipo, status, carga
- Colunas: Nº Carga, Tipo, Equipe, Separador(es), Unidade, Local, Peso, SKUs, Início, Fim, Duração (HH:MM:SS), Status, Ocorrências
- **Exportar CSV** - compatível com Excel (BOM UTF-8, separador `;`)

**Página: `/occurrence-report`**

**Relatório de Ocorrências** - Uma linha por ocorrência
- Cruzamento de dados com operação
- Filtros: data, carga, separador, tipo operação, unidade, tipo ocorrência
- **Exportar CSV** com todos os detalhes
- Facilita análise de problemas

### 🎯 SLA

**Dashboard SLA (`/sla`)** *(admin only)*

Monitoramento em tempo real:
- KPIs: Finalizados, Dentro do SLA, Violações, Em Andamento
- **Operações em andamento** com cronômetro ao vivo
- **Lista de violações** (ultrapassou o limite)
- Comparação com meta configurada

**Metas SLA (`/sla-goals`)** *(admin only)*

Configurar limites de desempenho:
- Tempo médio por SKU (min)
- Tempo médio por tonelada (min)
- Tempo médio por carregamento (min)
- Máx. ocorrências por dia
- Peso mínimo por dia (kg)

Ativar/desativar metas para aparecer nos gráficos.

### 👥 Gerenciamento de Usuários

**Página: `/users`** *(admin only)*

Gerenciar todos os usuários:
- **Convidar** novo usuário (email + role inicial)
- **Alterar role** via select inline
- **Reset de senha** (padrão: 1234)
- Visualizar status (ativo/inativo)

### ⚙️ Configurações

**Página: `/settings`** *(admin only)*

Personalizar a aplicação:
- Nome do sistema
- Descrição
- Cores primária e secundária
- Upload de logo

Mudanças aplicadas imediatamente em toda a interface.

---

## 🗄️ Estrutura do Banco de Dados

**SQLite com 9 entidades:**

```
User (autenticação)
├── id, email, password_hash, full_name, role, active
├── created_date, updated_date

Separator (colaboradores)
├── id, full_name, separator_id, active
├── created_date, updated_date

OperationUnit (filiais)
├── id, name, code, active
├── created_date, updated_date

OperationLocation (locais por unidade)
├── id, name, unit_id, unit_name, active
├── created_date, updated_date

LoadOperation (operações)
├── id, team_type, separator_1, separator_1_name
├── separator_2, separator_2_name, operation_type
├── unit_id, unit_name, location_id, location_name
├── load_number, weight_kg, sku_count
├── start_time, end_time, duration_minutes
├── status, occurrence_count
├── created_date, updated_date, created_by

Occurrence (problemas)
├── id, load_operation_id, item_code, description
├── quantity, occurrence_type
├── created_date, updated_date

OccurrenceType (tipos de problema)
├── id, name, description, active
├── created_date, updated_date

SLAGoal (metas de desempenho)
├── id, name, metric, target_value, unit, active
├── created_date, updated_date

AppConfig (configurações)
├── id, app_name, app_description
├── logo_filename, primary_color, secondary_color
├── updated_date
```

**Criado automaticamente ao iniciar a aplicação!**

---

## 🎨 Design e UX

### 🎭 Estilo Visual
- **Sidebar retrátil** com gradiente moderno
- **Cards com hover effects** e sombras elegantes
- **Badges coloridas** para status e roles
- **Tabelas responsivas** com overflow
- **Formulários intuitivos** com validação
- **Topbar com info do usuário** e menu rápido

### 📱 Responsividade
- ✅ Desktop (1920+px) - Sidebar completa
- ✅ Tablet (768-1024px) - Sidebar adaptada
- ✅ Mobile (<768px) - Sidebar ícones apenas

### 🎯 Cores Dinâmicas
- Cores primária e secundária configuráveis
- Aplicadas em botões, badges, gradientes
- Salvas no banco de dados

---

## 📚 Exemplos de Uso

### Criar nova operação
```
1. Ir para /operation
2. Clicar "Nova Separação"
3. Selecionar:
   - Tipo de Equipe: Individual ou Dupla
   - Separador(es)
   - Tipo de Operação: Venda ou Transferência
   - Unidade
   - Local (opcional)
   - Nº Carregamento
   - Qtd. SKUs
   - Peso (opcional)
4. Confirmar → Operação criada em "Não Iniciado"
```

### Iniciar e finalizar operação
```
1. Na seção "Não Iniciado", clicar "Iniciar"
   → Operação passa para "Em andamento"
   → start_time é carimbado automaticamente
   → Cronômetro começa a rodar

2. Quando terminar, clicar "Finalizar"
   → Operação passa para "Finalizado"
   → end_time é carimbado
   → duration_minutes é calculado (HH:MM:SS)
```

### Registrar ocorrências
```
1. Na seção "Finalizados", clicar "Ocorrências"
2. Adicionar linhas com:
   - Código do item (SKU)
   - Descrição do problema
   - Quantidade afetada
   - Tipo de ocorrência (avaria, troca, etc)
3. Salvar → contador atualiza automaticamente
```

### Gerar relatório
```
1. Ir para /reports
2. Aplicar filtros (data, separador, tipo, status)
3. Ver tabela com todas as operações
4. Clicar "Exportar" → download CSV
5. Abrir em Excel mantendo formatação
```

---

## 🔧 Configuração Avançada

### Alterar porta
Editar `app.py`, última linha:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Mudou para 5001
```

### Usar outro banco de dados
Editar `app.py`, linha 20:
```python
# PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:pass@localhost/db'

# MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://user:pass@localhost/db'
```

### Ambiente de produção
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## 🐛 Troubleshooting

### ❌ "Port 5000 already in use"
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :5000
kill -9 <PID>
```

### ❌ "ModuleNotFoundError: No module named 'flask'"
```bash
# Verificar se ambiente virtual está ativado
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Reinstalar
pip install -r requirements.txt
```

### ❌ "Database is locked"
```bash
# Fechar outras instâncias
# Deletar monitor_separacao.db
# Reiniciar aplicação
```

### ❌ Esqueceu a senha do admin
```bash
# Deletar banco de dados
rm monitor_separacao.db

# Reiniciar
python app.py

# Login: admin@localhost / admin
```

---

## 📞 Suporte

**Checklist se algo não funcionar:**

- [ ] Python versão 3.8+ instalado (`python --version`)
- [ ] Ambiente virtual ativado
- [ ] Dependências instaladas (`pip list`)
- [ ] Pasta `templates/` existe com todos os `.html`
- [ ] Pasta `static/uploads/` criada
- [ ] Porta 5000 disponível
- [ ] Executando `python app.py` sem erros

---

## 📊 Métricas Calculadas

### Tempo (sempre em HH:MM:SS)

```
Tempo Médio/SKU = Σ (duração das operações) / Σ (total de SKUs)
Tempo Médio/Ton = Σ (duração das operações) / Σ (peso em toneladas)
Tempo Médio/Carga = Σ (duração das operações) / (número de operações)
```

### Status

- **Não Iniciado** → Criada, não iniciada
- **Em andamento** → Iniciada, em execução
- **Finalizado** → Concluída com duração calculada

### Roles

- **admin** → Acesso total
- **operator** → Operações, relatórios, ocorrências
- **pending** → Bloqueado até aprovação

---

## 🎁 Bônus

### Dados de teste inclusos
- 1 admin padrão (admin@localhost / admin)
- Banco pronto para começar a usar
- Sem configuração adicional necessária

### Validações implementadas
- Email único
- Senha obrigatória na criação
- Dupla requer 2 separadores
- Data/hora automáticas
- Duração calculada automaticamente
- Contador de ocorrências sincronizado

---

## 📝 Licença

Desenvolvido para **R&J Logistics** - Monitor de Separação

---

## 🎉 Pronto para usar!

```bash
# Resumo do início rápido:
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate no Windows
pip install -r requirements.txt
python generate_templates.py
python app.py
```

**Acesse: http://localhost:5000** 🚀

---

**Versão:** 1.0.0  
**Python:** 3.8+  
**Framework:** Flask 3.0.0  
**Database:** SQLite  
**Último update:** 2024
