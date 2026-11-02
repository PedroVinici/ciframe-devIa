# Relatório de testes — Sequências de Acordes Customizadas

## Cobertura

Não existe suíte de testes formal no repositório (sem pytest/unittest configurado).
A verificação foi feita de duas formas:

1. **Script exploratório `test_order_preserving_match.py`** (raiz do repo): compara,
   para as 6 sequências originais, o resultado atual por `seqs_famosas` com o novo
   match contíguo em `Musica.cifra` (função `match_contiguous_sequence`, linha 54).
2. **Checagens de backend com o Flask test client e com servidor HTTP real**:
   - `GET /sequencias` retorna as 6 sequências semeadas (`main.py:209`).
   - `POST /sequencias` cria (201 + `id`), rejeita duplicata (409), lista vazia (400)
     e corpo inválido (400) (`main.py:224`).
   - `GET /similares?sequencia_id=<id>` usa match contíguo, mantém paginação de 100,
     filtro por gênero e o formato legado `sequencia=C,G,Am,F` (`main.py:340-376`).
   - Persistência: sequência criada continua disponível após reabrir o banco.
   - `match_contiguo` (`main.py:340`): acerto contíguo, rejeição quando há acorde no
     meio, alvo maior que a cifra e lista vazia.
   - Assets estáticos: `/`, `/templates/cadastra-seqfamosa.html` e
     `/assets/js/controllers/cadastra-seqfamosa.js` respondem 200.
3. **Sintaxe do frontend**: `node --check` em `sequencia.js`, `cadastra-seqfamosa.js`
   e `routes.js`.
4. **Docker com volume**: build da imagem, run com `-v "$(pwd)/data:/app/data"`,
   criação de sequência via POST e reinício do container para confirmar a persistência.

## Teste de regressão obrigatório

Critério adotado: **superconjunto**, não igualdade. O novo algoritmo é intencionalmente
mais permissivo (match contíguo em `cifra`), então ele pode encontrar mais músicas, mas
não pode perder nenhuma que o critério antigo (`seqs_famosas`) encontrava. A seed das
originais agora fica em `SEQUENCIAS_ORIGINAIS` (`main.py:105`).

Resultado (`get_similares_por_sequencia_custom` vs. `seqs_famosas`, sem paginação):

| Sequência | ID | Tags (`seqs_famosas`) | Contíguo | Faltando |
|-----------|----|-----------------------|----------|----------|
| BmGDA     | 0  | 199                   | 866      | 0        |
| CGAmF     | 1  | 296                   | 1216     | 0        |
| EmG       | 2  | 4                     | 3110     | 0        |
| CA7DmG7   | 3  | 5                     | 96       | 0        |
| GmF       | 4  | 7                     | 1039     | 0        |
| CC7FFm    | 5  | 3                     | 132      | 0        |

Todas as músicas marcadas com tag continuam sendo encontradas (`faltando = 0` em todos
os casos), confirmando a regressão.

## Como rodar

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python test_order_preserving_match.py
```

As checagens de endpoints foram feitas com o Flask test client, por exemplo:

```
PYTHONPATH=. python -c "
import main
c = main.app.test_client()
print(c.get('/sequencias').status_code)
print(c.post('/sequencias', json={'acordes': ['C','G','D','A']}).status_code)
print(c.get('/similares?sequencia_id=1').status_code)
"
```

## Persistência no Docker

Build e execução com o mesmo volume documentado no deploy:

```
docker build -t ciframe .
docker run -d --name ciframe-persist-test -p 8090:8080 -v "$(pwd)/data:/app/data" ciframe
```

Resultado:

- `GET /generos` → 200; `GET /sequencias` → 8 sequências existentes (IDs 0–7).
- `POST /sequencias` com `{"acordes":["D","F#","A","D"]}` → 201, `id=8`.
- Container parado/removido e um novo container subido com o mesmo volume:
  `GET /sequencias` continuou retornando `id=8` e
  `GET /similares?sequencia_id=8` retornou 13 músicas na primeira página.
- Limpeza: a linha de teste (`id=8`) foi removida do `data/sequencias.db`; o
  catálogo voltou às sequências 0–7.

Observação: sem `.dockerignore`, o `COPY . .` copiou o `data/sequencias.db` local
para dentro da imagem; em runtime o volume sobrescreve o arquivo. Isso não afeta a
persistência, mas convém adicionar `.dockerignore` (ver revisão de código).

## O que ficou de fora

- **Teste de navegador (E2E)** do fluxo `#/porsequencia` → `#/cadastra-seqfamosa` →
  POST → redirect com a sequência selecionada. A lógica foi revisada e a sintaxe
  validada, mas não houve clique real no browser.
- **Docker sem volume**: não foi validado o cenário sem bind mount; nesse caso as
  sequências criadas em runtime ficam apenas na camada gravável do container e são
  perdidas ao removê-lo.
- **Concorrência**: não foram testados POSTs simultâneos (risco de `database is locked`).
- **Validação de acordes desconhecidos**: o POST aceita qualquer string não vazia; não
  há teste para acordes fora do conjunto conhecido.
- **Formato legado `sequencia=`**: testado apenas para as 6 sequências semeadas.
- **Frontend automatizado**: não há testes unitários de controllers AngularJS.
