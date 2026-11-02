# deciframe codebase research (current state)

Repository snapshot: `fb97001` (`master`, clean working tree) on 2026-10-31.
This document records only what the repository contains and what the code does
today. Runtime observations below were made by importing `main` with the
declared Flask version in a temporary environment and calling it through
Flask's test client.

## Summary

deciframe is a single-process Flask application that loads
`data/top/dataset_final.csv` into memory at import time and serves both a JSON
API and a static AngularJS 1.4.9 frontend from the same origin. The dataset is
interpreted through fixed positional columns declared in `main.py`, producing
67,585 `Musica` objects at runtime, 52 genre keys, and 6,653 distinct chord
tokens. Search has two independent paths: title/artist token search over
`nome_artista`/`nome_musica`, and chord/sequence similarity over unique chord
sets, with optional genre filtering and a 100-item pagination helper. Famous
sequence search is tag-based and recognizes exactly six hardcoded chord strings;
there is no database, write endpoint, authentication layer, or custom-sequence
creation path. The frontend uses CDN-hosted AngularJS/jQuery with no build step,
and Flask serves `index.html`, static assets, and Angular templates from the
same process; the Docker image runs `gunicorn main:app` on port 8080.

## Repository inventory

The Git tree contains 166 tracked files. The application code is concentrated
in `main.py`, `musica.py`, and `static/`; the rest is data, offline scripts,
documentation, and assets.

| Path | Current role |
|---|---|
| `main.py` | Flask app, CSV loader, in-memory indexes, all API routes |
| `musica.py` | Single `Musica` domain class |
| `Dockerfile` | Python 3.9 slim image, gunicorn entrypoint |
| `requirements.txt` | `Flask==3.1.3`, `gunicorn==23.0.0` |
| `static/index.html` | AngularJS host page and CDN script list |
| `static/assets/js/` | Angular module, routes, controllers, directives, bundled `ngprogress` |
| `static/templates/` | Angular route templates and directive templates |
| `static/assets/css/` | Application styling and icon font CSS |
| `data/top/dataset_final.csv` | Runtime song catalog (15,866,887 bytes) |
| `data/` | Source/raw datasets and offline pipeline inputs |
| `scripts/` | Download/parse/normalize pipeline scripts |
| `docs/adr/` | Architecture decision records |
| `docs/features/sequencias-customizadas/` | Coursework statement and phase templates |
| `README.md`, `AGENTS.md`, `CONTRIB.md` | Project, agent, and contribution docs |

There is no test directory, test framework config, `package.json`, or CI
configuration. The only file with `test` in its name is
`docs/features/sequencias-customizadas/04-test-report.md`, a template.

## Runtime and deployment

### Docker path

`Dockerfile:1-12` builds from `python:3.9-slim`, copies `requirements.txt`,
installs dependencies, copies the repository into `/app`, exposes port 8080,
and starts:

```
gunicorn --bind 0.0.0.0:8080 main:app
```

`requirements.txt:4-5` pins `Flask==3.1.3` and `gunicorn==23.0.0`. The
container has no database service, volume, or external runtime dependency.

### Direct Python path

`main.py:279-280` runs `app.run(debug=True)` only when `main.py` is executed
directly, which serves on Flask's default port 5000. The README documents 8080
for Docker and 5000 for the virtualenv path (`README.md:11-31`).

### Deployment decisions

`docs/adr/0001-local-only-docker-deploy.md:1-16` records the move away from App
Engine `python27` and Heroku configuration to the local-only Dockerfile.
`docs/adr/0003-lift-frontend-freeze.md:1-21` records that touching the legacy
AngularJS frontend is no longer prohibited, while the stack itself remains
AngularJS 1.4.9 + jQuery. `docs/adr/0002-persist-custom-sequences.md:1-8` is an
unfilled ADR template for introducing persistence for custom sequences.

### Static file serving

`Flask(__name__)` uses the repository's `static/` directory as its static
folder (`main.py:9`). `GET /` returns `index.html` via
`app.send_static_file('index.html')` (`main.py:101-103`), and
`GET /<path:path>` forwards any other unmatched path to
`app.send_static_file(path)` (`main.py:109-112`). Because `index.html` uses
relative paths such as `assets/js/app.js` and Angular templates such as
`templates/home.html` (`static/index.html:136-147`, `static/assets/js/routes.js:3-25`),
those files are served through the catch-all static route when the app is
opened at `/`.

The Flask route table contains both the catch-all and the API routes; requests
such as `/search`, `/generos`, and `/musica/<id>/` reach their specific view
functions, while `/assets/...` and `/templates/...` fall through to the static
proxy. Unknown paths return Flask's 404 page; for example `/nope` returned
`404 text/html`.

### CORS and response type

`main.py:274-277` adds `Access-Control-Allow-Origin: *` to every response.
Every API route returns `json.dumps(...)` as a Python string rather than
`jsonify`, so responses are served as `Content-Type: text/html; charset=utf-8`
(also documented in `AGENTS.md:43-46`). Runtime checks confirmed this for all
API endpoints.

## Backend bootstrap and domain model

### CSV loading at import

`main.py:49-98` opens `data/top/dataset_final.csv` at module import, calls
`f.readline()` once, then iterates the remaining lines. The CSV has no header:
its first physical row is data (`14-bis,a-qualquer-tempo,...`). Consequently
that first row is not loaded into memory. The next row,
`14-bis,adoraveis-criaturas,...`, is the first CSV row represented in the
running app.

The positional columns are declared at `main.py:25-35`:

| Index | Constant | Meaning |
|---|---|---|
| 0 | `ARTISTA_ID` | artist slug |
| 1 | `MUSICA_ID` | song slug |
| 2 | `ARTISTA` | display artist name |
| 3 | `MUSICA` | display song name |
| 4 | `GENERO` | genre label |
| 5 | `POPULARIDADE` | view count |
| 6 | `TOM` | musical key |
| 7 | `SEQ_FAMOSA` | semicolon-separated famous-sequence ids |
| 8 | `CIFRA` | semicolon-separated chord sequence |

Each line is transformed before splitting (`main.py:52-63`):

- `line.replace('"', '').replace('NA', '')[:-1]` removes every quote
  character, removes every literal uppercase `NA` substring anywhere in the
  line, and drops the trailing newline.
- `line.split(',')` splits the result into nine fields.
- `musica[POPULARIDADE] = int(musica[POPULARIDADE].replace('.', ''))` converts
  the view count to an integer after removing thousands separators.
- Empty `CIFRA` becomes `[]`; otherwise `limpa_cifra` is applied to the
  semicolon-split chord field.
- `SEQ_FAMOSA` is split on `;`.

`limpa_cifra` (`main.py:11-23`) drops blank tokens. For tokens containing
`|`, it takes the text before `|`, splits on whitespace, and keeps the first
token. For other tokens it splits on whitespace and extends the chord list with
all pieces.

### Current dataset shape

Measured against `data/top/dataset_final.csv` and the loaded process:

| Measure | Value |
|---|---|
| Physical CSV rows | 67,586 (no header) |
| Rows loaded into `main.musicas` | 67,585 |
| Bytes on disk | 15,866,887 |
| Loaded genre keys | 52 |
| Distinct cleaned chord tokens | 6,653 |
| `SEQ_FAMOSA` values after parsing | `''` 67,071; `1` 296; `0` 199; `4` 7; `3` 5; `2` 4; `5` 3 |

The 52 genre values loaded by the backend are:
`Alternativo`, `Axé`, `Blues`, `Bolero`, `Bossa Nova`, `Brega`, `Clássico`,
`Country`, `Disco`, `Eletrônica`, `Emocore`, `Folk`, `Forró`, `Funk Carioca`,
`Gospel/Religioso`, `Grunge`, `Guarânia`, `Gótico`, `Hard Rock`, `Hardcore`,
`Heavy Metal`, `Hip Hop/Rap`, `Indie`, `Industrial`, `Infantil`,
`Instrumental`, `Jazz`, `Jovem Guarda`, `MPB`, `Marchas/Hinos`, `New Wave`,
`Pagode`, `Pop`, `Pop Rock`, `Power-Pop`, `Psicodelia`, `Punk Rock`, `R&B;`,
`Reggae`, `Regional`, `Rock`, `Rock Progressivo`, `Rockabilly`, `Romântico`,
`Samba`, `Samba Enredo`, `Sertanejo`, `Soft Rock`, `Soul`, `Surf Music`,
`Velha Guarda`, `World Music`. The `R&B;` value includes the semicolon in the
loaded genre string.

### `Musica` model

`musica.py:1-25` defines the only domain object. Its constructor stores
`id_artista`, `nome_artista`, `id_musica`, `nome_musica`, `genero`,
`popularidade`, `tom`, `cifra`, and `seqs_famosas`. It derives:

- `self.acordes = list(set(cifra))` (`musica.py:17`): unique chords, in
  set-iteration order.
- `self.id_unico_musica = '%s_%s' % (id_artista, id_musica)`
  (`musica.py:20`).
- `self.url = 'http://www.cifraclub.com.br/%s/%s' % (id_artista, id_musica)`
  (`musica.py:22`).

`__str__` returns `id_unico_musica,genero,popularidade` (`musica.py:24-25`).

### In-memory indexes built at startup

`main.py:37-47` initializes the global state:

- `genero_musicas = {}`: genre string to list of `Musica`.
- `generos = set()`: unique genre strings.
- `acordes = set()`: unique chord tokens.
- `sequencias`: hardcoded mapping of sequence strings to integer ids:
  `BmGDA -> 0`, `CGAmF -> 1`, `EmG -> 2`, `CA7DmG7 -> 3`, `GmF -> 4`,
  `CC7FFm -> 5` (`main.py:40-45`).
- `musicas_dict = {}`: `id_unico_musica` to `Musica`.

During the CSV loop (`main.py:65-85`):

- Each genre is added to `generos`.
- Each `Musica` is stored in `musicas_dict` by `id_unico_musica`.
- Every chord from `musica.acordes` is added to `acordes`.
- Each `Musica` is appended to `genero_musicas[genero]`.

After the loop (`main.py:87-98`):

- `musicas` is an `OrderedDict` of `musicas_dict` sorted by
  `popularidade` descending.
- `generos` is converted from a set to a list.
- Every list in `genero_musicas` is sorted by `popularidade` descending.

Import completed successfully in the verification environment and produced
`len(musicas) == 67585`, `len(generos) == 52`, and `len(acordes) == 6653`.

## HTTP API

All API routes are defined in `main.py`. No route accepts a request body and
no route writes data. Genre and chord parameters are comma-separated query
strings. The page parameter is read as a string, defaulting to `'1'`
(`main.py:117`, `main.py:176`).

| Route | Parameters | Behavior |
|---|---|---|
| `GET /` | none | Serves `static/index.html` |
| `GET /<path:path>` | path | Serves a file from `static/` |
| `GET /search` | `key` (required), `generos` (optional), `pagina` (optional) | Title/artist token search, paginated |
| `GET /musicas` | none | Returns every loaded `Musica.__dict__` |
| `GET /generos` | none | Returns the `generos` list |
| `GET /acordes` | none | Returns the `acordes` set as a list |
| `GET /musica/<m_id>/` | path id | Returns one `Musica.__dict__` |
| `GET /similares` | `acordes` or `id_unico_musica` or `sequencia`, plus `generos` and `pagina` | Similarity search |

### `/search` (`main.py:114-142`)

`request.args.get('key').lower()` is called without a default, so a request
without `key` raises an exception and returns 500. The lowercased query is
accent-stripped with `remover_combinantes` (`main.py:145-147`), which normalizes
to NFD and drops Unicode `Mn` combining marks, then split on single spaces.

The genre filter defaults to the full `generos` list; if `generos` is present
it is split on `,`. `apply_filtro` builds the candidate collection
(`main.py:266-272`). For each `Musica`, the code builds
`'%s %s' % (nome_artista.lower(), nome_musica.lower())`, strips accents the
same way, splits on spaces, and requires `all(key in text_list for key in keys)`
(`main.py:128-131`). Matches are serialized with only
`id_unico_musica`, `id_artista`, `id_musica`, `nome_artista`, `nome_musica`,
`genero`, and `url` (`main.py:132-140`). Results are passed through
`get_pagina` (`main.py:226-228`), which returns
`colecao[(pagina-1)*100:(pagina-1)*100+100]`.

Observed behavior: `/search?key=adoraveis` returned the one matching song;
`/search?key=` returned a page of results because the empty query becomes
`['']`, and `''` occurs in the split text list; `/search` returned 500.
`/search?key=beatles` returned 100 results and a 26,963-byte JSON string.

### `/musicas` (`main.py:154-156`)

Returns `json.dumps([v.__dict__ for v in musicas.values()])`, i.e. all 67,585
loaded songs in popularity-sorted order. The response observed was 48,590,307
bytes. The adjacent comment (`main.py:149-153`) describes a paginated service,
but the route itself applies no pagination.

### `/generos` (`main.py:158-160`)

Returns `json.dumps(generos)`. The list is derived from a set, so its order is
the list's current set-derived order; no sort is applied. Response size was
665 bytes.

### `/acordes` (`main.py:162-164`)

Returns `json.dumps(list(acordes))`. Observed response size was 68,010 bytes.

### `/musica/<m_id>/` (`main.py:166-168`)

Looks up `musicas[m_id]` by exact `id_unico_musica` and returns its
`__dict__`. The route requires the trailing slash in its declaration. A valid
id such as `14-bis_adoraveis-criaturas` returned 200 and a 1,037-byte object.
An id for the skipped first CSV row (`14-bis_a-qualquer-tempo`) returned 500
because it is not in `musicas`.

### `/similares` (`main.py:170-201`)

The handler reads `acordes`, `id_unico_musica`, `sequencia`, `pagina`, and
`generos`. It selects an input source with this precedence:

1. If `acordes` is present, `acordes = acordes_tag.split(',')`.
2. Else if `id_unico_musica` is present, it looks up that song in `musicas`
   and uses `musica.acordes`.
3. Else if `sequencia` is present, it removes commas from the sequence string
   and performs tag-based sequence lookup only.

Genre filtering defaults to all genres; otherwise the `generos` value is split
on `,` (`main.py:178-182`).

For chord and song inputs, `get_similares` (`main.py:230-263`) filters the
collection by genre and loops over every song except the input song id when
one was supplied. For each song it computes:

- `inter = set(acordes).intersection(set(musica.acordes))`
- `diff = set(musica.acordes) - set(acordes)`

A song is included only when `len(inter) > 0`. Included objects contain
`id_unico_musica`, `id_artista`, `id_musica`, `nome_artista`, `nome_musica`,
`popularidade`, `acordes`, `genero`, `url`, `diferenca` (list from `diff`), and
`intersecao` (list from `inter`) (`main.py:246-258`). The returned list is
sorted by `(len(x['diferenca']), -len(x['intersecao']))` (`main.py:263`).
The preceding comment mentions popularity, but the sort key contains only
difference and intersection terms. Python's stable sort preserves the
candidate collection order for equal keys.

Candidate order comes from `apply_filtro`: it concatenates each requested
genre's popularity-sorted list. With no `generos` parameter it iterates the
`generos` list, which is derived from a set, so the base collection is grouped
by genre rather than globally sorted by popularity.

Observed behavior: `/similares?acordes=C`, `/similares?acordes=C,G`, and
`/similares?acordes=C,G,Am,F` each returned 100 items (the page limit).
`/similares?acordes=ZZZ` returned `[]`; `/similares` with no input parameters
returned `[]`.

For song input, `/similares?id_unico_musica=14-bis_adoraveis-criaturas`
returned 100 results (38,871 bytes). The lookup uses the same `musicas`
dictionary as `/musica/<m_id>/`; a missing id raises `KeyError` and returns
500. A valid id excludes that id from its own result list (`main.py:238`).

### Famous-sequence lookup (`main.py:190-197`, `main.py:203-223`)

When `sequencia` is supplied, the handler removes all commas from the query
string, then checks the result against the six keys in `sequencias`. If it is
one of the six, it calls `get_similares_por_sequencia(id_seq, generos_key)`,
which filters by genre and includes songs where
`str(id_seq) in musica.seqs_famosas`. Unknown sequence strings return
`[]` without scanning song chords.

Observed tag matches before pagination: sequence `0` 199 songs, `1` 296,
`2` 4, `3` 5, `4` 7, `5` 3. Because `get_pagina` caps responses at 100,
`BmGDA` and `CGAmF` each returned 100 items; the other four returned all their
matches.

The six sequences are named in `data/mapeamento_sequencias_famosas.txt:1-6`:

| id | Chords | Name in file |
|---|---|---|
| 0 | `Bm G D A` | Sequência de Bm |
| 1 | `C G Am F` | Sequência de C |
| 2 | `Em G` | Sequência Em |
| 3 | `C A7 Dm G7` | Sequência de C (Samba) |
| 4 | `Gm F` | Sequência de Gm |
| 5 | `C C7 F Fm` | Sequência de C (Samba cont.) |

### Genre filtering (`main.py:266-272`)

`apply_filtro` loops over the requested genre strings and appends the matching
list from `genero_musicas` only when the genre exists in the `generos` set.
Unknown genres contribute nothing. Repeated genres append the same list again.
The returned list is used by `/search`, `/similares`, and
`get_similares_por_sequencia`.

## Similarity semantics present in the code

- Chord comparison is exact string matching between the requested chord tokens
  and `Musica.acordes`, which is built from the cleaned CSV chord field.
- `Musica.acordes` is de-duplicated by `list(set(cifra))`; repeat counts and
  original chord order are not retained in that attribute. `Musica.cifra`
  retains the cleaned ordered list.
- Chord order is not part of the chord-similarity comparison; only set
  intersection and difference are used.
- No case folding, enharmonic normalization, slash-chord normalization, or
  other chord rewriting occurs in the request path.
- Sequence matching does not inspect `Musica.cifra`; it checks the
  precomputed `seqs_famosas` tag list for the sequence's integer id.
- Title/artist search is exact token containment after lowercasing and accent
  removal; it does not use substring/prefix matching per token.

## Frontend

### Host page and dependency loading

`static/index.html:1-149` declares `<html lang="pt" ng-app="deciframeApp">`
and loads Bootstrap 3.3.6 CSS/JS, jQuery 1.11.3, AngularJS 1.4.9, angular-route,
angular-animate, angular-ui-bootstrap 2.1.4, and local `ngprogress` from CDNs or
local files (`static/index.html:13-20`, `static/index.html:125-147`). There is
no frontend build step.

The page includes the main navigation, a hidden menu panel with project/team
copy, and `<div class="page" ng-view></div>` for routed templates
(`static/index.html:22-123`). Google Analytics is initialized with tracking id
`UA-85286010-1` (`static/index.html:25-32`).

### Angular module, constants, and routes

`static/assets/js/app.js:1-58` creates module `deciframeApp` with `ngRoute`,
`ngAnimate`, `ngProgress`, and `ui.bootstrap`. It defines two constants:

- `RESTAPI = { url: 'http://localhost:5003' }` (`app.js:3-5`). No controller
  references this constant; the controllers declare local `apiUrl = ""`.
- `GENEROS`, a 51-entry hardcoded genre list (`app.js:6-58`).

The frontend `GENEROS` list excludes `R&B;`, which is present in the backend's
52-genre list, and includes the same other labels.

`static/assets/js/routes.js:1-29` maps:

| Hash route | Template | Controller |
|---|---|---|
| `#/` | `templates/home.html` | `HomeController` |
| `#/poracordes` | `templates/acordes.html` | `AcordesController` as `Chords` |
| `#/pormusica` | `templates/musica.html` | `MusicaController` as `Musica` |
| `#/porsequencia` | `templates/sequencia.html` | `SequenciaController` as `Sequencia` |
| `#/sobre` | `templates/about.html` | `AboutController` |
| otherwise | redirect to `/` | |

### `MainController`

`static/assets/js/controllers/main.js:1-12` defines `showMenu`, `toggleMenu`,
and `isActive(path)`, which tests `$route.current.regexp` against a path.

### Home (`HomeController` and `home.html`)

`static/assets/js/controllers/home.js:1-4` sets `pageTitle` and `pageClass`.
`static/templates/home.html:1-90` renders the animated sphinx directive, the
deciframe SVG logo, and three navigation panels linking to `#/poracordes`,
`#/pormusica`, and `#/porsequencia`.

### Chords page (`AcordesController` and `acordes.html`)

`static/assets/js/controllers/acordes.js:1-124` defines seven chord groups
(C through B), including major, minor, and seventh variants (`acordes.js:2-44`).
It exposes `acordes` as the grouped grid, `meusAcordes` as selected chords,
`generos` from the `GENEROS` constant, and a progress-bar instance.

- `addAcorde` toggles a chord in `meusAcordes` and calls
  `pesquisarPorAcordes` (`acordes.js:63-71`).
- `temAcorde` tests selection (`acordes.js:72-74`).
- `createChordsString` joins selected chord labels with commas
  (`acordes.js:76-82`).
- `pesquisarPorAcordes` calls
  `similares?acordes=<chords>` and appends `&generos=<selected>` when a genre
  is selected (`acordes.js:84-115`). `apiUrl` is `""`, so the request is
  relative to the current origin.
- Results are stored in `vm.musics`; `goToLirics` opens `music.url`;
  `goToResults` scrolls to the results section (`acordes.js:117-124`).

`static/templates/acordes.html:1-96` renders the chord grid, the selected
chords, a genre `<select>`, exact-match cards where
`music.diferenca.length` is zero (`acordes.html:41-59`), and a second
"aprenda mais alguns acordes" section for songs with a non-empty `diferenca`
(`acordes.html:61-91`). Each result is ordered client-side by
`-popularidade` (`acordes.html:42`, `acordes.html:66`).

### Song page (`MusicaController` and `musica.html`)

`static/assets/js/controllers/musica.js:1-80` implements typeahead search:

- `getMusicas(val)` calls `search?key=<val>` and returns
  `response.data` through Angular's `$http.then` (`musica.js:14-20`).
- `pesquisarPorMusica(musica)` optionally stores the selected song, then calls
  `similares?id_unico_musica=<id>` and appends `&generos=<selected>`
  (`musica.js:43-70`).
- `goToLirics` and `goToResults` mirror the chords page (`musica.js:72-79`).

`static/templates/musica.html:1-119` configures the typeahead with
`typeahead-min-length="3"`, `typeahead-wait-ms="1000"`, and
`typeahead-on-select="Musica.pesquisarPorMusica(minhaMusica)"`
(`musica.html:13-18`). It renders the selected song, exact-match result cards,
and the "learn more chords" section using `music.diferenca` hex badges
(`musica.html:46-113`).

### Sequence page (`SequenciaController` and `sequencia.html`)

`static/assets/js/controllers/sequencia.js:2-37` hardcodes four sequence
objects in the frontend:

| Frontend variable | Chords | Corresponding backend id |
|---|---|---|
| `sequencia1` | `Bm G D A` | 0 |
| `sequencia2` | `C G Am F` | 1 |
| `sequencia3` | `Gm F` | 4 |
| `sequencia4` | `C C7 F Fm` | 5 |

The frontend does not include backend sequences 2 (`Em G`) or 3
(`C A7 Dm G7`). `sequenciasFamosas` is populated from these four objects
(`sequencia.js:33-37`). `pesquisarPorSequencia` calls
`similares?sequencia=<comma-joined chords>` and appends the optional genre
(`sequencia.js:63-90`). `limparPesquisa` clears the selected sequence and
results (`sequencia.js:92-95`). There is no form, POST, or other path for
creating a sequence.

`static/templates/sequencia.html:1-63` renders the four clickable sequence
groups, a genre selector, and result cards. It displays only the
exact-match section (`ng-hide="music.diferenca.length"`,
`sequencia.html:40-59`); unlike the chords and song templates, it has no
"learn more chords" section.

### About page

`static/assets/js/controllers/about.js:1-4` sets `pageTitle = 'Sobre'` and
`pageClass = 'page-about'`; `static/templates/about.html:1-9` renders the title
inside a panel. The route is present in `routes.js:22-25`.

### Directives and templates

- `df-hex` (`static/assets/js/directives/df-hex.js:1-12`) is an element
  directive with isolate scope `acorde` (`@`), `acordeColor` (`@`),
  `acordeChecked` (`=`), and `small` (`=`), using
  `templates/directives/df-hex.html`. The template draws an SVG hexagon and
  label, filling white when checked and using `acordeColor` otherwise
  (`static/templates/directives/df-hex.html:1-9`).
- `df-esfinge` (`static/assets/js/directives/df-esfinge.js:1-9`) is an element
  directive with `dfAnimated` (`=`) and uses
  `templates/directives/df-esfinge.html`, a 326-line animated SVG sphinx
  (`static/templates/directives/df-esfinge.html:1-326`).

### Styling

`static/assets/css/app.css:1-652` contains the full visual styling: page
transition classes, logo fill classes, panel color variants A-F
(`app.css:77-86`), chord hex sizing (`app.css:161-196`), menu/team styles,
music cards (`app.css:263-301`), form controls, result-count button, and
keyframe animations. `static/assets/css/icons.css:1-36` defines the icon font
classes, with font files under `static/assets/css/fonts/`. Images are
`static/assets/img/deciframe.png` and `static/assets/img/team.png`.

### Frontend files not referenced by the routed app

- `static/assets/js/controllers/search.js:1-25` defines `SearchController`
  with mock "Californication" results and an `$http.get("")` call. It is not
  listed in `static/index.html:136-147` and no route or template references
  `SearchController`.
- `static/bower.json:1-26` declares a Bower dependency on
  `ng-material-floating-button`; `static/.bowerrc:1-3` points the install
  directory at `assets/vendor`. No `static/assets/vendor` directory is tracked,
  and `static/index.html` does not load that dependency. `static/assets/vendor`
  is also ignored in `.gitignore:1`.
- The `RESTAPI` constant in `static/assets/js/app.js:3-5` points at
  `http://localhost:5003`, while controllers use relative URLs.

## Data assets

### Runtime catalog

`data/top/dataset_final.csv` is the only dataset read by the running app. It
has 9 positional columns as described above, no header row, and 67,586 physical
rows. The first physical row is `14-bis,a-qualquer-tempo,...`; the app skips it
at `main.py:50`.

The CSV's first physical line (skipped by the app) is:

```
14-bis,a-qualquer-tempo,14 Bis,A Qualquer Tempo,MPB,70115,B,NA,E;F#;E;F#;...
```

No physical row has an empty `CIFRA`, but 8,141 rows contain the literal `NA`
chord field; the loader removes `NA`, leaving an empty string and therefore an
empty `Musica.cifra`/`acordes` list. 805 rows have an empty `TOM`; no row has
an empty or non-numeric `POPULARIDADE`. `SEQ_FAMOSA` is `NA` for 67,072
physical rows; after the loader's `NA` removal those rows become an empty
string and then a `['']` list via `split(';')`.

### Supporting data files

| Path | Content observed |
|---|---|
| `data/top/artista_musica_estilo.txt` | `artist_slug,<artist>_<song>,style` lines |
| `data/top/top_artistas.txt` | CifraClub artist URLs |
| `data/top/top_artistas.txt_*.songs` | Partitioned song URL lists |
| `data/top/visualizacoes.csv` | `artist,song,views` with dot-separated views |
| `data/top/visualizacoes_pontos.csv` | Visualization/popularity points input |
| `data/top/chords-transitions-empty.csv` | Header of 42 roman-numeral transition columns |
| `data/top/url-estilos.txt` | Genre URLs |
| `data/top/html_estilos/*.html` | Saved CifraClub genre pages, 75 files |
| `data/top/merge_datasets.R` | Joins song dataset and visualization data |
| `data/top/popularidade.R` | Sums views by artist |
| `data/artistas_por_letra.txt` | Seed artist URL list |
| `data/estilos.html` | Saved CifraClub genre index page |
| `data/mapeamento_sequencias_famosas.txt` | Names for sequence ids 0-5 |
| `data/transposition_matrix2.csv` | Key-to-roman-numeral matrix used by R scripts |
| `data/dataset_seq_notas.csv` | 23,458,857-byte dataset with `ARTISTA`, `MUSICA`, `ESTILO`, `TOM`, `VISUALIZACOES`, `CIFRA`, `NCIFRA` |
| `data/data-cavaco.csv` | 460,858-byte `artista,musica,tom,sequencia` dataset |
| `data/cavaco_htlms.tar.gz` | 23,566,724-byte archive of saved HTML |
| `data/url-artistas*.txt` | Artist URL lists |
| `data/teoria` | Plain text chord-field/key reference |

`data/teoria` is a 330-byte text file, not a directory. It contains four
"campo harmônico" lines for F, C, G, and D, plus a four-row note table for C, G,
D, and F major.

## Offline data pipeline

The `scripts/` directory contains download, parse, normalization, and
transition-building utilities. The Python scripts use Python 2 syntax
(`print` statements, `reload(sys)`, `sys.setdefaultencoding`) and are not
imported by the running Flask app.

### Download and parse

| Script | Current contents |
|---|---|
| `scripts/download_band_names.sh:1-11` | Reads a URL list, derives an output name from the CifraClub URL, and `curl`s each artist page |
| `scripts/download_cifras.sh:1-9` | Reads a song URL list, derives artist/song path parts, and `curl`s each into `cifras_erro/<artist>/` |
| `scripts/collect_song_list.sh:1-6` | Runs `DownloadAll` with `jsoup-1.8.3.jar` |
| `scripts/DownloadAll.java:1-73` | Jsoup scraper; reads artist URL list, collects song links containing the band slug, writes `.songs` files in chunks of 25,000 |
| `scripts/cifra_parser.py:1-27` | Parses saved CifraClub HTML into `artist,song,key,chords` |
| `scripts/parse_estilos.py:1-22` | Parses `data/estilos.html` into CifraClub genre URLs |
| `scripts/parse_artistas_estilos.py:1-29` | Contains a file-walk loop and a commented-out HTML parser block |
| `scripts/generate_data_set.py:1-92` | Parses saved HTML into the nine-column dataset, including famous-sequence tagging |

`generate_data_set.py:7-24` defines the original six sequence strings in
lowercase (`bm;g;d;a`, `c;g;am;f`, `em;g`, `c;a7;dm;g7`, `gm;f`, `c;c7;f;fm`).
For each chord sequence it lowercases the song chord string, checks whether the
sequence string is a substring, then verifies that every song token is in the
sequence tokens. Matching ids are collected and emitted as the `SEQ_FAMOSA`
field. The script also extracts key, genre, artist name, song name, chord
sequence, and view count from saved HTML (`generate_data_set.py:41-89`).

`scripts/add_estilos.py:1-45` reads the song dataset and
`artista_musica_estilo.txt`, maps artist to style, and writes a CSV named
`test.csv` in the working directory.

### R normalization and aggregation

| Script | Current contents |
|---|---|
| `scripts/merge_datasets.R` (in `data/top/merge_datasets.R:1-15`) | Reads `dataset.csv` and `visualizacoes_pontos.csv`, joins on artist/song, selects `ARTISTA, MUSICA, VISUALIZACOES, TOM, CIFRA`, writes `dataset_final.csv` without row names |
| `data/top/popularidade.R:1-9` | Reads `dataset_final.csv` and summarizes views by artist |
| `scripts/add_estilos.R:1-10` | Left-joins the song dataframe with the artist/style file |
| `scripts/normalize_chords.R:1-40` | Converts chord strings to roman-numeral strings using `data/transposition_matrix2.csv`; splits chords on `;`, takes the first character, maps a `#` to `base.` notation, and writes `NCIFRA` |
| `scripts/simplify_chords.R:1-36` | Same conversion logic, returning a vector and joining it as `NCIFRA` |
| `scripts/build-chords-transitions.R:1-77` | Builds transition counts from `NCIFRA`; defines `get_chords_transitions`, `fill_transitions_df`, and `build_transitions_df`; reads `chords-transitions-empty.csv` and `dataset_seq_notas.csv`; the final line references `musicas_df`, which is not defined earlier in that file |

`data/top/merge_datasets.R:12-15` names the final output
`dataset_final.csv`, which is the file `main.py` reads. The current
`dataset_final.csv` contains nine columns, while the `select` in that R script
names five (`ARTISTA`, `MUSICA`, `VISUALIZACOES`, `TOM`, `CIFRA`).

## Documentation and coursework files

### Project docs

- `README.md:1-35` describes the product, stack, Docker and virtualenv run
  commands, contribution pointer, and license pointer.
- `AGENTS.md:1-47` records stack versions, run/verify commands, and three
  gotchas: dataset reload requires restart, endpoint responses are
  `json.dumps` strings with `text/html`, and deploy changes should consult
  `docs/adr/`.
- `CONTRIB.md:1-38` contains the repository's contributor-license and
  Google Cloud sample-app contribution text. It references individual and
  corporate CLAs and the `GoogleCloudPlatform/Template` repository.
- `LICENSE:1-5` begins the Apache License, Version 2.0.
- `.playground:1-13` contains an App Engine starter descriptor naming
  `main.py`, `app.yaml`, and `appengine_config.py`; the latter two files are not
  in the current tree.

### ADRs

| File | State |
|---|---|
| `docs/adr/0001-local-only-docker-deploy.md:1-16` | Filled: replaces App Engine/Heroku config with local Dockerfile |
| `docs/adr/0002-persist-custom-sequences.md:1-8` | Unfilled template with bracketed placeholders and instructions |
| `docs/adr/0003-lift-frontend-freeze.md:1-21` | Filled: lifts the frontend freeze while keeping the legacy stack |

### `docs/features/sequencias-customizadas/`

This directory contains a course assignment, not an implemented feature:

- `00-enunciado.md:1-130` states the task: let any visitor register a new
  chord sequence and search by it, persist the sequence catalog in a database,
  reflect the backend catalog in `#/porsequencia`, keep music/genre data in the
  CSV, keep the single local Dockerfile, keep the six original sequences
  producing the same results, and keep `json.dumps(...)` responses.
- `01-research.md:1-44` is a research template with four questions covering
  matching algorithm, hypothesis validation, embedded database choices, and the
  current `#/porsequencia` frontend.
- `02-proposal.md:1-49` is an unfilled proposal template covering algorithm,
  database, schema, API, frontend, alternatives, and scope.
- `03-plan.md:1-33` is an unfilled implementation-plan template naming
  `main.py`, `musica.py`, `static/assets/js/controllers/sequencia.js`,
  `static/templates/sequencia.html`, and a new schema/migration.
- `04-test-report.md:1-25` is an unfilled test-report template.

The current code has no database dependency, no persistence layer, no
sequence-creation endpoint, and no frontend form for creating sequences. The six
sequences in `main.py` and the four sequences in `sequencia.js` are the complete
sequence catalog present in the running application.

## Cross-component connections and data flows

### Startup flow

```
data/top/dataset_final.csv
  -> main.py:49-98 import-time parse
     -> limpa_cifra()            main.py:11-23
     -> Musica(...)              musica.py:1-25
     -> musicas_dict / musicas   main.py:74, 88-89
     -> genero_musicas           main.py:82-85, 95-96
     -> generos / acordes sets   main.py:66, 77-78, 92
```

When the process starts, all catalog state is built in module globals. A file
change is not re-read by a running process.

### Browser load

```
GET /                     -> main.py:101-103 -> static/index.html
GET /assets/js/app.js     -> main.py:109-112 -> static/assets/js/app.js
GET /templates/home.html  -> main.py:109-112 -> static/templates/home.html
```

Angular loads the module from `app.js`, reads routes from `routes.js`, and
requests the template named by the active hash route.

### Title/artist search flow

```
musica.html typeahead
  -> MusicaController.getMusicas(val)              musica.js:14-20
  -> GET search?key=<val>
  -> main.py:114-142 busca()
     -> remover_combinantes()                      main.py:145-147
     -> apply_filtro()                             main.py:266-272
     -> token containment check                    main.py:128-131
     -> get_pagina()                               main.py:226-228
  -> JSON array of id/name/genre/url objects
  -> typeahead selection
  -> MusicaController.pesquisarPorMusica(musica)   musica.js:43-70
  -> GET similares?id_unico_musica=<id>
  -> main.py:170-201 get_similares()
     -> musica.acordes                             musica.py:17
     -> get_similares()                            main.py:230-263
  -> result cards                                   musica.html:46-113
```

### Chords search flow

```
acordes.html chord click
  -> AcordesController.addAcorde()                 acordes.js:63-71
  -> AcordesController.pesquisarPorAcordes()       acordes.js:84-115
  -> GET similares?acordes=<comma-joined>
  -> main.py:170-201 get_similares()
     -> set intersection / difference              main.py:240-241
     -> sort by difference then intersection       main.py:263
     -> get_pagina()                               main.py:226-228
  -> exact-match cards and "learn more" cards      acordes.html:40-91
```

### Sequence search flow

```
sequencia.html sequence click
  -> SequenciaController.pesquisarPorSequencia()   sequencia.js:63-90
  -> GET similares?sequencia=<comma-joined>
  -> main.py:190-197 removes commas
  -> lookup in sequencias dict                     main.py:40-45, 194
  -> get_similares_por_sequencia()                 main.py:203-223
     -> genre filter                                main.py:205
     -> str(id) in musica.seqs_famosas             main.py:209
  -> get_pagina()                                   main.py:196
  -> result cards                                   sequencia.html:40-59
```

The frontend sequence list is not fetched from the backend; it is the four
hardcoded objects in `sequencia.js:2-37`. The backend sequence list is the six
keys in `main.py:40-45`. Both sides send/receive the same `similares` response
shape, but they do not share a catalog source.

### Asset and template serving

```
index.html relative asset paths
  -> GET /assets/... or /templates/...
  -> main.py:109-112 static_proxy()
  -> Flask static file lookup under static/
```

The API calls use the same origin because controllers leave `apiUrl` empty
(`acordes.js:91`, `musica.js:12`, `sequencia.js:72`); no controller uses the
`RESTAPI` constant.

## Observed endpoint results

These results were obtained by importing the current `main.py` with the
declared Flask version in a temporary environment and using Flask's test client.

| Request | Status | Observed response |
|---|---|---|
| `GET /` | 200 | `text/html`, 11,436 bytes, `index.html` |
| `GET /index.html` | 200 | same 11,436 bytes |
| `GET /assets/js/app.js` | 200 | `text/javascript`, 1,028 bytes |
| `GET /nope` | 404 | Flask 404 page, 207 bytes |
| `GET /search` | 500 | Flask 500 page, 265 bytes |
| `GET /search?key=` | 200 | JSON page of results, 27,850 bytes |
| `GET /search?key=adoraveis` | 200 | one result, 262 bytes |
| `GET /search?key=adoraveis%20criaturas` | 200 | same one result, 262 bytes |
| `GET /search?key=beatles` | 200 | 100 results, 26,963 bytes |
| `GET /search?key=beatles&pagina=2` | 200 | 100 results, 26,552 bytes |
| `GET /musicas` | 200 | 48,590,307 bytes |
| `GET /generos` | 200 | 665 bytes |
| `GET /acordes` | 200 | 68,010 bytes |
| `GET /musica/14-bis_adoraveis-criaturas/` | 200 | 1,037 bytes |
| `GET /musica/14-bis_a-qualquer-tempo/` | 500 | `KeyError` in `main.py:168` |
| `GET /similares` | 200 | `[]` |
| `GET /similares?acordes=ZZZ` | 200 | `[]` |
| `GET /similares?id_unico_musica=14-bis_adoraveis-criaturas` | 200 | 100 results, 38,871 bytes |
| `GET /similares?id_unico_musica=NOPE` | 500 | `KeyError` in `main.py:188` |
| `GET /similares?acordes=C` | 200 | 100 results |
| `GET /similares?acordes=C,G` | 200 | 100 results |
| `GET /similares?acordes=C,G,Am,F` | 200 | 100 results |
| `GET /similares?sequencia=XXXX` | 200 | `[]` |
| `GET /similares?sequencia=Bm,G,D,A` | 200 | 100 results |
| `GET /similares?sequencia=C,G,Am,F` | 200 | 100 results |
| `GET /similares?sequencia=Em,G` | 200 | 4 results |
| `GET /similares?sequencia=C,A7,Dm,G7` | 200 | 5 results |
| `GET /similares?sequencia=Gm,F` | 200 | 7 results |
| `GET /similares?sequencia=C,C7,F,Fm` | 200 | 3 results |
| `GET /similares?acordes=C&generos=Rock` | 200 | 100 results |
| `GET /similares?acordes=C&generos=Gospel/Religioso` | 200 | 100 results |
| `GET /similares?acordes=C&generos=Nope` | 200 | `[]` |
| `GET /similares?acordes=C&generos=Rock,Rock` | 200 | 100 results |

All 200 API responses reported `Content-Type: text/html; charset=utf-8`, and
the CORS header is added by `main.py:274-277`.
