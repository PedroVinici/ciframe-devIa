# Sequências Customizadas — Design Document

<!-- AGENT-IGNORE-START -->
***OBS: Nesse momento da atividade eu percebi que eu havia interepretado a atividade e essses arquivos de maneira errada, provavelmente eles era pra ser preenchido pelo agente, diretamente, como eu ja fiz muito coisa manualemnte e oque discuti com o agente esta no contexto da sessao que vou enviar, decidi não apagar tudo que já preenchi, apensa pedi para que o agente preenchesse `02-proposal.md` com a proposta que discutimos anteriormente :) mas não vou alterar o `01-research` justamente pq acredito que a proposta da skill de `/reearch-codebase` não eh fazer pesquisas direcionadas a uma feature, a ideia eh trazer um overview do codebase mesmo e o arquivo de reasearch induz o agente a procurar direcionado para a feature. Por isso, vou manter o arquivo  `/research/codebase-overview.md` com a pesquisa original que o agente realizou e de onde tirei algumas resposta para o preenchimento manual de `01-reaseach.md`**

***Após pedir que o agente perenchesse esse plan.md avaliei o plano e confirmei que está tudo alinhado com oque eu esperava. Provavelmente pq ja alinhamos muito bem a proposta, por mais que eu não tenha a salvo em 02-proposal.md***

***Percebi ainda que o agente não seguiu o formato de preenchimento que já existia nesse arquivo (Por mais que eu tenha pedido por isso no prompt), como o formato que ele preencheu me parece funcionar legal para que ele implemente a feature, resolvi manter o plano assim e pedir pela implmentaçao.***

<!-- AGENT-IGNORE-END -->

## Current Context
- Backend único `main.py` (Flask 3.1) carrega `data/top/dataset_final.csv` em memória no import; não há banco de dados.
- As 6 sequências "famosas" são hardcoded em `main.py:40-45` e resolvidas via tag pré-computada `seqs_famosas` em `get_similares_por_sequencia()` (`main.py:203-223`). Os nomes/listas estão em `data/mapeamento_sequencias_famosas.txt`.
- O endpoint `/similares?sequencia=...` (`main.py:190-197`) só reconhece essas 6 chaves; não calcula match em tempo real.
- Frontend AngularJS 1.4.9. `#/porsequencia` (`static/assets/js/routes.js:17-21`) usa lista hardcoded de 4 sequências em `static/assets/js/controllers/sequencia.js:2-37`, template em `static/templates/sequencia.html`.
- `#/poracordes` (`static/assets/js/routes.js:7-11`) já tem a UI de seleção de acordes por clique (`static/assets/js/controllers/acordes.js`, `static/templates/acordes.html`), reaproveitável para montar a sequência.
- `Musica.cifra` preserva ordem e repetições; `Musica.acordes` é `list(set(cifra))` (`musica.py`). O match da nova feature deve usar `cifra`.
- Infra: Dockerfile único, local-only (`docs/adr/0001-local-only-docker-deploy.md`). Músicas e gêneros continuam no CSV em memória; só o catálogo de sequências vai para banco.

## Requirements

### Functional Requirements
- Qualquer visitante cadastra uma sequência (lista ordenada de acordes), sem login; catálogo aberto e anônimo.
- Qualquer sequência (6 originais + novas) pode ser usada para buscar músicas, com os mesmos resultados esperados hoje para as 6 originais.
- Catálogo de sequências persistido em banco, sobrevivendo a reinícios do container.
- Nova tela `#/cadastra-seqfamosa`, acessível a partir de `#/porsequencia`, usando a mesma UI de escolha de acordes de `#/poracordes`.
- Após cadastrar (POST com sucesso), redirecionar para `#/porsequencia` com a nova sequência já selecionada, exibindo músicas filtradas no painel direito, mantendo o layout sequências (esquerda) / músicas (direita).
- `#/porsequencia` passa a refletir o catálogo real vindo do backend (sem lista hardcoded em JS).
- Conflitos (sequência ordenada idêntica) impedem a criação.
- Só o catálogo de sequências vai para o banco; `musicas`/`generos` continuam no CSV.
- Novo endpoint family com POST e GET.
- Match: a sequência deve aparecer **completa e exatamente na ordem** cadastrada, em qualquer parte de `Musica.cifra` (contíguo, sem acordes no meio). Sem normalização de input.
- Manter a mesma paginação de hoje.
- Respostas continuam `json.dumps(...)`, não `jsonify`.

### Non-Functional Requirements
- Persistência entre reinícios via volume Docker montado em `data/`.
- Baixo acoplamento: não migrar músicas/gêneros; não adicionar serviços externos.
- Compatível com o container único/local-only do ADR 0001.
- Custo de busca em tempo real aceitável para uso local (scan em memória filtrado por gênero).

## Design Decisions

### 1. Banco de dados: SQLite em arquivo
Usar SQLite (`sqlite3`, stdlib) em `data/sequencias.db` porque:
- Não exige serviço externo e cabe no container único/local-only do ADR 0001.
- Já disponível no Python 3.9 sem nova dependência em `requirements.txt`.
- Persistência garantida montando um volume em `data/`.
- Alternativas (Postgres/MySQL) foram descartadas por exigirem serviço externo.

### 2. Esquema mínimo, sem nome/timestamp
Tabela `sequencias(id INTEGER PRIMARY KEY, acordes_json TEXT NOT NULL UNIQUE)` porque:
- Só `id` e a sequência ordenada são necessários; `nome` e `timestamp` ficam fora de escopo.
- `UNIQUE(acordes_json)` implementa a regra de conflito (duplicata impede criação).

### 3. Seed das 6 originais na criação da tabela
Inserir as 6 sequências existentes logo após `CREATE TABLE IF NOT EXISTS`, com `INSERT OR IGNORE` e IDs fixos (0-5), porque:
- Garante paridade de regressão desde o primeiro boot, sem migração separada.
- IDs fixos preservam previsibilidade das 6 originais.

### 4. Catálogo sem cache em memória
`GET /sequencias` lê direto do banco e, na busca, a sequência é recuperada por ID no momento do match, porque:
- Não há vantagem em manter o catálogo em memória (diferente do CSV, que é caro de reler).
- Atende ao requisito de recuperar do banco e enviar direto ao front.

### 5. Matching contíguo em `Musica.cifra`
Buscar a sequência alvo como bloco contíguo: `cifra[i:i+len(target)] == target`, porque:
- "Aparecer completa e exatamente na ordem em qualquer parte da música" = match contíguo.
- `Musica.cifra` preserva ordem e repetições; `acordes` (set) não serve.
- Sem normalização: o input já vem da UI de acordes.

### 6. Novo endpoint family `GET/POST /sequencias`
Criar endpoints dedicados em vez de estender `/similares`, porque:
- A feature precisa de POST e GET; `/similares` é GET e legado.
- Isola o novo catálogo e o corte do mecanismo hardcoded/`seqs_famosas`.

### 7. IDs fixos começam em 0; frontend trata 0 como id válido
A sequência `BmGDA` recebe `id = 0`. O guard de busca em `static/assets/js/controllers/sequencia.js` deve testar `undefined`/`null`, não truthiness (`!id`), porque `0` é falsy em JavaScript e descartaria a busca. As demais sequências usam 1–5.

## Technical Design

### 1. Core Components
- `init_db()`: abre/cria `data/sequencias.db`, executa `CREATE TABLE IF NOT EXISTS` e faz o seed das 6 originais.
- `get_sequencias()`: `GET /sequencias` — lê todas as linhas e devolve `[{ "id": int, "acordes": [...] }, ...]`.
- `criar_sequencia()`: `POST /sequencias` — valida array não-vazio, serializa em JSON e insere; violação de `UNIQUE` retorna conflito.
- `match_contiguo(target, cifra)`: retorna `True` se `target` aparece como bloco contíguo em `cifra`.
- `get_similares_por_sequencia_custom(id_seq, generos_key, pagina)`: busca a sequência por ID no banco, aplica `apply_filtro()` por gênero, roda o match contíguo e pagina com `get_pagina()`.

### 2. Data Models
```sql
CREATE TABLE IF NOT EXISTS sequencias (
    id INTEGER PRIMARY KEY,
    acordes_json TEXT NOT NULL UNIQUE
);
```
- Seed (IDs fixos, ordem preservada):
  - `0`: `["Bm","G","D","A"]`
  - `1`: `["C","G","Am","F"]`
  - `2`: `["Em","G"]`
  - `3`: `["C","A7","Dm","G7"]`
  - `4`: `["Gm","F"]`
  - `5`: `["C","C7","F","Fm"]`
- `acordes_json` armazena a lista ordenada em JSON (ex.: `["C","G","Am","F"]`), usada tanto na exibição quanto no match e na detecção de duplicata.

### 3. Integration Points
- `GET /sequencias` → retorna o catálogo (consumido por `#/porsequencia`).
- `POST /sequencias` → body `{ "acordes": ["C","G","Am","F"] }`; cria ou retorna conflito.
- Busca por sequência → resolve `id` no banco, aplica `apply_filtro(musicas.values(), generos_key)`, match contíguo em `musica.cifra`, `get_pagina(...)` com `TAM_PAGINA` atual.
- Frontend:
  - `#/cadastra-seqfamosa` (nova rota em `static/assets/js/routes.js`) usa UI de `#/poracordes` para montar a lista ordenada e faz `POST /sequencias`.
  - Em sucesso, redireciona para `#/porsequencia` com o `id` da nova sequência; a tela auto-seleciona e dispara a busca.
  - `#/porsequencia` carrega o catálogo via `GET /sequencias`.
- Todas as respostas permanecem `json.dumps(...)`; CORS inalterado.

### 4. Files Changes
- `main.py` — init SQLite, seed, endpoints `GET/POST /sequencias`, fluxo de busca contíguo.
- `static/assets/js/routes.js` — nova rota `#/cadastra-seqfamosa`.
- `static/assets/js/controllers/sequencia.js` — catálogo via `GET /sequencias`, auto-seleção e busca.
- `static/assets/js/controllers/cadastra-seqfamosa.js` — novo controller de cadastro.
- `static/templates/sequencia.html` — ajuste do link/botão e integração do catálogo dinâmico.
- `static/templates/cadastra-seqfamosa.html` — novo template espelhando `acordes.html`.
- `README.md` / `AGENTS.md` — documentar `docker run` com volume em `data/` (se necessário).
- Nenhum outro arquivo deve ser impactado.

## Implementation Plan

1. Phase 1: Backend / persistência
   - Criar `init_db()` com `CREATE TABLE IF NOT EXISTS` e seed das 6 originais (`INSERT OR IGNORE`, IDs 0-5).
   - Implementar `GET /sequencias` e `POST /sequencias` (validação, conflito por `UNIQUE`, `json.dumps`).
   - Garantir abertura do banco em `data/sequencias.db` com volume montado.

2. Phase 2: Matching
   - Implementar `match_contiguo(target, cifra)`.
   - Adaptar a busca por sequência para resolver o `id` no banco, aplicar `apply_filtro()`, match contíguo e `get_pagina()`.
   - Cortar o uso do hardcoded `main.sequencias`/`seqs_famosas` para este fluxo.

3. Phase 3: Frontend
   - Adicionar rota `#/cadastra-seqfamosa` e link a partir de `#/porsequencia`.
   - Criar controller/template de cadastro espelhando `#/poracordes` (clique para montar a lista ordenada, `POST`, conflito, redirect).
   - Atualizar `#/porsequencia` para carregar `GET /sequencias` e auto-selecionar a sequência recém-criada.
   - Documentar o volume Docker.

## Testing Strategy

### Unit Tests
- `match_contiguo`: acerto contíguo, ausência, e caso com acorde no meio (não deve casar).
- `POST /sequencias`: array vazio inválido; duplicata retorna conflito e não insere.
- Serialização: `GET/POST` retornam string `json.dumps`.

### Integration Tests
- Regressão: seed das 6 originais; resultados idênticos aos atuais (mesmos conjuntos).
- Sequência `BmGDA` (`id = 0`) deve buscar normalmente; o guard do frontend não pode tratar `0` como id ausente.
- Fluxo: `#/porsequencia` → `#/cadastra-seqfamosa` → POST → redirect → nova sequência selecionada com resultados no painel direito.
- Persistência: criar sequência, reiniciar o container com volume, confirmar via `GET /sequencias`.
- Paginação igual à atual.
- Contrato: `musicas`/`generos` continuam do CSV; endpoints mantêm `json.dumps`.

## Observability

### Logging
- Não aplicável a esta mudança.

### Metrics
- Não aplicável a esta mudança.

## Future Considerations

### Potential Enhancements
- Cache em memória do catálogo caso o número de sequências cresça muito.
- Índices/estruturas para acelerar o match em catálogos grandes.

### Known Limitations
- Scan em tempo real sobre até ~67k músicas por busca (filtrado por gênero).
- Sem autenticação/moderação; catálogo anônimo e aberto.

## Dependencies

### Development Dependencies
- `sqlite3` (stdlib do Python 3.9).
- Flask/gunicorn já existentes; AngularJS 1.4.9 já existente.

## Security Considerations
- Catálogo aberto e anônimo por requisito; sem autenticação.
- Validar entrada (lista não-vazia, acordes vindos da UI) e evitar duplicatas.
- Sem dados pessoais ou segredos persistidos.

## Rollout Strategy
1. Desenvolvimento local.
2. Testes de regressão das 6 originais e do fluxo de cadastro.
3. Execução local via Docker com volume: `docker run -p 8080:8080 -v $(pwd)/data:/app/data ciframe`.
4. Primeiro boot cria `sequencias.db` e insere as 6 originais.

## References
- `docs/features/sequencias-customizadas/00-enunciado.md`
- `docs/features/sequencias-customizadas/01-research.md`
- `docs/features/sequencias-customizadas/02-proposal.md`
- `docs/adr/0001-local-only-docker-deploy.md`
- `research/codebase-overview.md`
- Template: `~/reppit-framework/templates/design_doc_template.md`

## Validation Notes
- Bug encontrado na validação manual: ao selecionar `BmGDA` (`id = 0`), o frontend não buscava porque `sequencia.js` usava `!vm.minhaSequencia.id` (0 é falsy). Corrigido para checar `undefined`/`null` explicitamente.
- Botões com label ilegível: a regra global `a:link { color: #FFF }` (`static/assets/css/app.css:123`) sobrescrevia o `color: #333` do Bootstrap nos links `.btn-default`, deixando texto branco sobre fundo branco em `#/porsequencia` e `#/cadastra-seqfamosa`. Corrigido em `static/assets/css/app.css` com regras explícitas de cor para `.btn-default` e `.btn-primary`.

<!-- AGENT-IGNORE-START -->
### Apos finalizar a implementação, notei alguns problemas na feature que o agente entregou:***
1. Os botões do front estava com as labels da mesma cor que o botão, oque impede a leitura do botão
2. Nenhuma das sequencias que ja existiam esta sendo listada, não sei dizer se não forma inseridas no banco ou se estão com problema na exibiçao
3. O cadastro das sequencias não esta funcionando. Sempre retorna "OPS, algo deu errado" sem um feedback significativo.

os pontos 2 e 3 estavam no plano de implementação, apenas o 1 de fato não foi discutido antes.

Simplismente rodei o `review-code` e aguardei a resposta. Algo que reparei agora eh que o agente por vezes esta acessando o `00-enunciado.md` dando uma burlada e lenda coisas além do plano que discutimos. Após essa pergunta ele respondeu com: 
````
Summary: Sim — a feature está implementada e o backend foi validado por HTTP real (GET/POST /sequencias, busca por sequencia_id, paginação e filtro), mas ainda falta o teste de clique no browser. O maior risco é a perda de compatibilidade com o formato legado ?sequencia=CGAmF; os demais itens são robustez, validação e pendências de documentação/entrega.
Action Items:
 1. 🔴 Restaurar o suporte ao formato legado concatenado em ?sequencia= (ex.: ?sequencia=CGAmF): o endpoint antigo removia as vírgulas e encontrava a sequência; hoje resolve_sequencia_id só tenta a lista com vírgulas/id e devolve [] (verificado: 0 resultados, antes eram 296). in main.py:292-310
 2. 🟡 Adicionar timeout ao sqlite3.connect e tratar sqlite3.OperationalError ("database is locked") no POST /sequencias, devolvendo erro controlado em vez de 500 sob concorrência. in main.py:115-138, main.py:224-250
 3. 🟡 Limitar o POST /sequencias anônimo (máx. de acordes, tamanho de cada string) e validar contra o conjunto de acordes conhecido, evitando catálogo poluído/abuso. in main.py:224-235
 4. 🟡 Criar .dockerignore (ou ajustar o COPY) para não assar data/sequencias.db local na imagem Docker. in Dockerfile:8
 5. 🟡 Ignorar .DS_Store no .gitignore (há ?? .DS_Store e ?? data/.DS_Store untracked). in .gitignore:1-5
 6. 🟡 Extrair os grupos de acordes duplicados entre as duas telas para uma constante/serviço compartilhado. in static/assets/js/controllers/acordes.js:2-44, static/assets/js/controllers/cadastra-seqfamosa.js:2-44
 7. 🟡 Corrigir o script de regressão: docstring fala em "subsequência" e a mensagem final diz "Resultados idênticos!", mas o critério implementado é bloco contíguo e superconjunto. in test_order_preserving_match.py:9, test_order_preserving_match.py:145
 8. 🟡 Completar a ADR 0002 no estilo da 0001 (título definitivo, contexto, alternativas, consequências); hoje é um parágrafo com placeholder e typo. in docs/adr/0002-persist-custom-sequences.md:1-4
 9. 🟡 Alinhar o plano com a implementação: incluir static/index.html/.gitignore na lista de arquivos e trocar "resultados idênticos" por "superconjunto (contíguo)". in docs/features/sequencias-customizadas/03-plan.md:113-121, docs/features/sequencias-customizadas/03-plan.md:149
10. 🟡 Registrar a demonstração no browser (gif/vídeo) e validar o fluxo #/porsequencia → #/cadastra-seqfamosa → redirect, ainda não coberto. in docs/features/sequencias-customizadas/04-test-report.md
11. 🟢 Remover o código morto do fluxo antigo (sequencias e o uso de seqs_famosas) depois de confirmar que nenhum cliente/teste depende deles. in main.py:41-45, musica.py:18
12. 🟢 Evitar alocação de slices em match_contiguo (comparar em loop) se o catálogo crescer; hoje é aceitável para ~67k músicas. in main.py:340-348
````
Confesso que já não sei distiniguir oque ele implmentou com base nas nossas discussões e oque ele burlou e acabou implementando observando diretamente o `00-enunciado.md`

* o item 1 eh de fato o mais preocupante segundo o agente e após rodar o review percebi que o própio agente ja consegui resolver a reclamação 2 e 3 originais que eu tinha, sobre as sequencias antigas nao aperecerem no front e sobre o cadastro. Os botões continuam inconsistentete. 
* Pedi primeiro que ele conrrigisse o ponto 1 que ele encontrou e registrasse no plano. Nesse pedido, o agente acabou explicando que esse ponto so eh um problema se quisermos manter o endpoint legado funcionando garantido essa regressao, como nao eh algo que acho que faça sentido, não pedi que ele solucionasse. 
* Percebi testando o fluxo no front que a primeira sequencia antiga de id 0, nao estava retornando nenhuma musica, pedi que o agente corrigisse e funcionou. 
* Vou solicitar agora apenas a modificação dos botões.
* Acabei de perceber também que não temos um mecanismo para excluir sequencias, uma coisa que não tinha percebido durante todo o fluxo de implementação. O fato de não termos associado usuarios a sequencias também ddificulta esse ponto.
* O agente implementou a mudança nos botões e pedi que ele atualizasse o plano com as modificações que realizamos.
* Vou rodar o /review novamente.
* Analisei o `04-test-report.md` acerdito que o teste de regressão realizado pelo agente foi suficiente para mostrar que todas as músicas retornadas pelo formato anterior continuam sendo retornadas agora. 
* Dos pontos levantados pelo review, o único que me chamou atenção foi: `- **Docker com volume**: não foi feito build/run do container nem reinício para confirmar a persistência via data/sequencias.db `. Por isso, pedi que o agente avaliasse esse ponto. Nesse moomento atingi o limite de uso free do OPENCODE KKKKKKKKKK, por isso, vou considerar a atividade finalizada. 


<!-- AGENT-IGNORE-END -->
