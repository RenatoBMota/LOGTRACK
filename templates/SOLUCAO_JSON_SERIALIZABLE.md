# 🔧 SOLUÇÃO GENÉRICA: TypeError JSON Serializable em TODOS os Templates

## ❌ Problema Universal
Qualquer template que tente usar `{{ variavel|tojson }}` vai dar erro:
```
TypeError: Object of type LoadOperation is not JSON serializable
```

## ✅ Solução: Padrão Jinja2

### PADRÃO PARA QUALQUER OBJETO:

#### ❌ NUNCA FAÇA:
```jinja
<script>
const data = {{ operations|tojson }};
const goals = {{ sla_goals|tojson }};
const units = {{ units|tojson }};
</script>
```

#### ✅ SEMPRE FAÇA:
```jinja
<script>
const data = [
    {% for item in operations %}
    {
        id: {{ item.id }},
        name: '{{ item.name }}',
        value: {{ item.value or 0 }},
        created_date: '{{ item.created_date.isoformat() if item.created_date else '' }}'
    }{{ ',' if not loop.last else '' }}
    {% endfor %}
];
</script>
```

---

## 📋 Checklist: Quais Dados Você Usa?

### Dashboard
- ✅ `operations` - CORRIGIDO
- ✅ `sla_goals` - CORRIGIDO

### SLA
- ✅ `operations` - CORRIGIDO
- ✅ `sla_goals` - CORRIGIDO
- ✅ `units` - CORRIGIDO
- ✅ `locations` - CORRIGIDO

### Relatórios
- ✅ `operations` - CORRIGIDO
- ✅ `occurrences` - CORRIGIDO
- ✅ `units` - CORRIGIDO
- ✅ `locations` - CORRIGIDO
- ✅ `occurrence_types` - CORRIGIDO

### Cadastros
- ✅ `separators` - Jinja2 puro (sem JSON)
- ✅ `units` - Jinja2 puro (sem JSON)
- ✅ `locations` - Jinja2 puro (sem JSON)
- ✅ `occurrence_types` - Jinja2 puro (sem JSON)

### Operation (card de operações)
- ✅ `separators` - Jinja2 puro
- ✅ `units` - Jinja2 puro
- ✅ `locations` - Jinja2 puro
- ✅ `occurrence_types` - Jinja2 puro

---

## 🔍 Como Identificar o Problema

Se você ver no console:
```
TypeError: Object of type ... is not JSON serializable
```

**Procure por:** `{{ variavel|tojson }}`

**Substitua por:** Loop Jinja2 manual

---

## 🛠️ Técnicas por Tipo de Dado

### 1. NÚMERO (inteiro ou decimal)
```jinja
{{ objeto.numero or 0 }}
```
✅ Resultado: `42` ou `0`

### 2. STRING
```jinja
'{{ objeto.texto }}'
```
✅ Resultado: `'valor'`

### 3. DATA/DATETIME
```jinja
'{{ objeto.data.isoformat() if objeto.data else '' }}'
```
✅ Resultado: `'2026-05-08T13:10:03'`

### 4. BOOLEANO
```jinja
{{ objeto.ativo|lower }}
```
✅ Resultado: `true` ou `false`

### 5. NULO/VAZIO
```jinja
{{ objeto.valor or 'null' }}
{{ objeto.valor or 0 }}
{{ objeto.valor or '' }}
```
✅ Resultado: Valor padrão se vazio

### 6. RELATIONSHIP (relação com outro objeto)
```jinja
'{{ objeto.relacionamento.nome }}'
```
✅ Resultado: Nome do objeto relacionado

---

## 📚 Exemplos Completos

### Exemplo 1: Conversão de Operações

```jinja
<!-- ❌ ERRADO -->
<script>
const ops = {{ operations|tojson }};
</script>

<!-- ✅ CORRETO -->
<script>
const ops = [
    {% for op in operations %}
    {
        id: {{ op.id }},
        load_number: '{{ op.load_number }}',
        status: '{{ op.status }}',
        sku_count: {{ op.sku_count or 0 }},
        weight_kg: {{ op.weight_kg or 0 }},
        duration_minutes: {{ op.duration_minutes or 0 }},
        created_date: '{{ op.created_date.isoformat() if op.created_date else '' }}',
        unit_id: {{ op.unit_id or 'null' }},
        location_id: {{ op.location_id or 'null' }},
        operation_type: '{{ op.operation_type or '' }}',
        team_type: '{{ op.team_type or '' }}',
        separator_1_name: '{{ op.separator_1_name or '' }}',
        separator_2_name: '{{ op.separator_2_name or '' }}',
        unit_name: '{{ op.unit_name or '' }}',
        location_name: '{{ op.location_name or '' }}',
        occurrence_count: {{ op.occurrence_count or 0 }}
    }{{ ',' if not loop.last else '' }}
    {% endfor %}
];
</script>
```

### Exemplo 2: Conversão de Metas SLA

```jinja
<!-- ❌ ERRADO -->
<script>
const goals = {{ sla_goals|tojson }};
</script>

<!-- ✅ CORRETO -->
<script>
const goals = [
    {% for goal in sla_goals %}
    {
        id: {{ goal.id }},
        name: '{{ goal.name }}',
        metric: '{{ goal.metric }}',
        target_value: {{ goal.target_value }},
        unit: '{{ goal.unit }}',
        active: {{ goal.active|lower }}
    }{{ ',' if not loop.last else '' }}
    {% endfor %}
];
</script>
```

### Exemplo 3: Conversão de Ocorrências

```jinja
<!-- ❌ ERRADO -->
<script>
const occs = {{ occurrences|tojson }};
</script>

<!-- ✅ CORRETO -->
<script>
const occs = [
    {% for occ in occurrences %}
    {
        id: {{ occ.id }},
        load_operation_id: {{ occ.load_operation_id }},
        item_code: '{{ occ.item_code or '' }}',
        description: '{{ occ.description or '' }}',
        quantity: {{ occ.quantity or 0 }},
        occurrence_type: '{{ occ.occurrence_type or '' }}'
    }{{ ',' if not loop.last else '' }}
    {% endfor %}
];
</script>
```

---

## 🔧 Se Tiver Mais Templates

### Passo 1: Identifique o erro
```
TypeError: Object of type ... is not JSON serializable
```

### Passo 2: Encontre a linha
```jinja
{{ variavel|tojson }}  ← AQI ESTÁ O PROBLEMA
```

### Passo 3: Substitua pelo padrão
```jinja
[
    {% for item in variavel %}
    {
        id: {{ item.id }},
        campo1: '{{ item.campo1 }}',
        campo2: {{ item.campo2 or 0 }}
    }{{ ',' if not loop.last else '' }}
    {% endfor %}
]
```

---

## ✅ Templates Já Corrigidos

- ✅ **dashboard.html** - Operações e SLA Goals serializadas
- ✅ **sla.html** - Operações, Goals, Units, Locations serializadas
- ✅ **relatorios.html** - Operações, Ocorrências, Units, Locations serializadas
- ✅ **cadastros.html** - Usa Jinja2 puro (sem JSON)

---

## 📥 Se Tiver Outros Templates

Se você criou outros templates e eles dão erro de serialização:

1. **Abra o arquivo**
2. **Procure por `|tojson`**
3. **Substitua usando o padrão acima**
4. **Teste no navegador**

---

## 🎯 Dica de Ouro

**Nunca use `|tojson` com objetos do banco de dados!**

Use apenas com dados já em Python puro:
```jinja
<!-- ✅ FUNCIONA -->
{{ {'a': 1, 'b': 2}|tojson }}

<!-- ❌ NÃO FUNCIONA -->
{{ objeto_do_banco|tojson }}
```

---

## 🐛 Se Tiver Outros Erros

### Erro: `name 'operationsData' is not defined`
**Causa:** Variável JavaScript não foi criada
**Solução:** Verifique se o `<script>` está antes do código que usa

### Erro: `SyntaxError: Unexpected token`
**Causa:** JSON inválido (vírgula no final, etc)
**Solução:** Use `{{ ',' if not loop.last else '' }}` para evitar trailing comma

### Erro: `undefined is not a function`
**Causa:** Campo não existe no objeto
**Solução:** Use `or` filter: `{{ obj.campo or '' }}`

---

## ✨ Resumo Final

| Situação | Faça | Não Faça |
|----------|------|----------|
| Dados Python puros | `{{ dict\|tojson }}` | - |
| Objetos do banco | Loop Jinja2 | `{{ obj\|tojson }}` |
| Relationship | `{{ obj.rel.campo }}` | `{{ obj.rel\|tojson }}` |
| Datas | `{{ data.isoformat() }}` | `{{ data\|tojson }}` |
| Números | `{{ numero }}` | - |
| Strings | `'{{ texto }}'` | - |

---

## 🚀 Próximas Ações

1. ✅ Download dos 4 templates corrigidos
2. ✅ Copie para a pasta `templates/`
3. ✅ Reinicie Flask
4. ✅ Teste todas as telas
5. ✅ Pronto! Sem mais erros de serialização

**Status: ✅ SOLUÇÃO UNIVERSAL IMPLEMENTADA**
