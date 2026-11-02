# Proposta — Sequências de Acordes Customizadas

## Abordagem escolhida

Persistir apenas o catálogo de sequências em SQLite e calcular o match em tempo real, a cada busca, sobre `Musica.cifra` (que preserva ordem e repetições). O catálogo é recuperado do banco sob demanda — sem cache em memória — e exposto por um novo endpoint family (`GET`/`POST /sequencias`). As 6 sequências originais são semeadas na criação da tabela para garantir paridade de regressão. No frontend, uma nova tela `#/cadastra-seqfamosa` reaproveita a UI de seleção de acordes de `#/poracordes` e, após o cadastro, redireciona para `#/porsequencia` com a sequência recém-criada já selecionada.

### Algoritmo de matching

Uma música é compatível com uma sequência quando a lista ordenada de acordes da sequência aparece **completa, exatamente na ordem e de forma contígua** em algum trecho de `Musica.cifra`. Acordes no meio invalidam a sequência.

Implementação: comparar sub-arrays de `cifra` com o alvo:

```
for i in range(len(cifra) - len(target) + 1):
    if cifra[i : i + len(target)] == target:
        return True
return False
```

- Usa `Musica.cifra` (não `acordes`, que é `list(set(...))` e perde ordem/repetições).
- Sem normalização de input: o usuário monta a sequência a partir da mesma lista de acordes da UI.
- O alvo é recuperado do banco pelo `id` no momento do match; a coleção é filtrada por gênero com `apply_filtro()` e paginada com `get_pagina()`, como hoje.

### Banco de dados

SQLite (`sqlite3`, stdlib do Python 3.9), em `data/sequencias.db`, persistido por um volume Docker montado em `data/`.

- Não exige serviço externo e cabe no container único/local-only do `docs/adr/0001-local-only-docker-deploy.md`.
- Sem nova dependência em `requirements.txt`.
- Só o catálogo de sequências vai para o banco; músicas e gêneros continuam vindo do CSV em memória, como hoje.

### Esquema de dados (alto nível)

Uma única tabela, sem `nome` e sem `timestamp`:

```
sequencias(id INTEGER PRIMARY KEY, acordes_json TEXT NOT NULL UNIQUE)
```

- `acordes_json` guarda a lista ordenada em JSON (ex.: `["C","G","Am","F"]`).
- `UNIQUE(acordes_json)` implementa a regra de conflito: sequência duplicada impede a criação.
- Seed das 6 originais logo após `CREATE TABLE IF NOT EXISTS`, com `INSERT OR IGNORE` e IDs fixos (0–5):
  - `0`: `["Bm","G","D","A"]`
  - `1`: `["C","G","Am","F"]`
  - `2`: `["Em","G"]`
  - `3`: `["C","A7","Dm","G7"]`
  - `4`: `["Gm","F"]`
  - `5`: `["C","C7","F","Fm"]`

### API

Novo endpoint family dedicado (não reutiliza `/similares`, que é GET e legado):

- `GET /sequencias` — lista o catálogo direto do banco: `[{ "id": <int>, "acordes": ["...", ...] }, ...]`.
- `POST /sequencias` — body `{ "acordes": ["C","G","Am","F"] }` (lista ordenada). Valida array não-vazio, serializa e insere. Duplicata retorna conflito e não cria.
- A busca por sequência resolve o `id` no banco, roda o match contíguo e mantém a paginação atual.
- Catálogo aberto e anônimo: qualquer visitante cadastra, sem login.
- Respostas continuam `json.dumps(...)` (não `jsonify`); CORS inalterado.

### Frontend

- Nova rota `#/cadastra-seqfamosa`, acessível a partir de `#/porsequencia`.
- O "form" reaproveita fielmente a UI de escolha de acordes de `#/poracordes` (`static/templates/acordes.html` + `static/assets/js/controllers/acordes.js`): todos os acordes em tela, clique para montar a lista ordenada, clique novamente para remover.
- Envio via `POST /sequencias`; conflito é exibido ao usuário.
- Em sucesso, redireciona para `#/porsequencia` com a nova sequência já selecionada, exibindo as músicas filtradas no painel direito — mantendo o layout atual (sequências à esquerda, músicas à direita).
- `#/porsequencia` passa a carregar o catálogo real de `GET /sequencias` (sem a lista hardcoded em `static/assets/js/controllers/sequencia.js`).

## Alternativas consideradas e descartadas

- **Pré-computar os matches e persistir os `id_unico_musica` de cada sequência no banco.** Seria mais rápido na leitura, mas fere a regra da atividade de persistir **apenas** o catálogo de sequências (músicas continuam no CSV), além de gerar escrita em massa (milhares de linhas por sequência), armazenamento extra e risco de dados desatualizados. Descartada.
- **Manter o catálogo em memória, carregado no boot como o CSV.** Não traz vantagem: diferente do CSV, ler poucas sequências do banco sob demanda é barato. Descartada.
- **Estender `/similares?sequencia=...` em vez de criar endpoints novos.** Não atende ao requisito de um endpoint family com POST e GET e mistura o mecanismo legado (`seqs_famosas`). Descartada.
- **Subsequência com acordes no meio (gaps).** Encontra músicas demais e não representa "a sequência aparece"; foi corrigida para match contíguo. Descartada.

## Escopo explícito

**Dentro do escopo:**

- Inserir as 6 sequências existentes no banco na criação da tabela (seed com IDs fixos).
- Novo endpoint family `GET/POST /sequencias`.
- Match contíguo em tempo real sobre `Musica.cifra`, com filtro de gênero e paginação atuais.
- Nova tela `#/cadastra-seqfamosa` espelhando `#/poracordes` e redirect para `#/porsequencia` com auto-seleção.
- `#/porsequencia` consumindo o catálogo do backend.
- Persistência via volume Docker em `data/`.
- Regressão obrigatória das 6 originais.

**Fora do escopo (e por quê):**

- Colunas `nome` e `timestamp` nas sequências: não são necessárias para a feature.
- Migrar músicas/gêneros para o banco: a atividade exige que continuem no CSV em memória.
- Autenticação/login ou moderação do catálogo: o catálogo é aberto e anônimo por requisito.
- Pré-computação de matches: quebra a regra de persistir apenas as sequências.
