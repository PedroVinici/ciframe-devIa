# coding: utf-8
import json
import sqlite3
from flask import Flask, request
import sys
from musica import *
from collections import OrderedDict
import unicodedata

app = Flask(__name__)

def limpa_cifra(raw_cifra):
    cifra = []
    for m in raw_cifra:
        if m.strip() != '':
            # filtra tablaturas
            if '|' in m:
                acorde = m.split('|')[0].split()[0]
                cifra.append(acorde)
            # lida com acordes separados por espaço
            else:
                tokens = [token for token in m.split()]
                cifra += tokens
    return cifra

# colunas do csv
ARTISTA_ID = 0
MUSICA_ID = 1
ARTISTA = 2
MUSICA = 3
GENERO = 4
POPULARIDADE = 5
TOM = 6
SEQ_FAMOSA = 7
CIFRA = 8
TAM_PAGINA = 100

genero_musicas = {}
generos = set()
acordes = set()
sequencias = {'BmGDA' : 0,
        'CGAmF' : 1,
        'EmG' : 2,
        'CA7DmG7' : 3,
        'GmF' : 4,
        'CC7FFm' : 5}

musicas_dict = {}

f = open('data/top/dataset_final.csv')
f.readline()

for line in f:
    line = line.replace('"', '').replace('NA', '')[:-1]

    musica = line.split(',')
    musica[POPULARIDADE] = int(musica[POPULARIDADE].replace('.', ''))

    if musica[CIFRA] != '':
        musica[CIFRA] = limpa_cifra(musica[CIFRA].split(';'))
    else:
        musica[CIFRA] = []

    musica[SEQ_FAMOSA] = musica[SEQ_FAMOSA].split(";")

    # conjunto único de gêneros
    generos.add(musica[GENERO])

    # inclui música no dict de músicas
    musica_obj = Musica(musica[ARTISTA_ID], musica[ARTISTA],
            musica[MUSICA_ID], musica[MUSICA], musica[GENERO],
            int(musica[POPULARIDADE]), musica[SEQ_FAMOSA],
            musica[TOM], musica[CIFRA])

    musicas_dict[musica_obj.id_unico_musica] = musica_obj

    # conjunto único de acordes
    for acorde in musica_obj.acordes:
        acordes.add(acorde)

    # constrói dict mapeando gênero para músicas
    # deve ser usado para melhorar o desempenho das buscas
    if musica_obj.genero in genero_musicas:
        genero_musicas[musica_obj.genero].append(musica_obj)
    else:
        genero_musicas[musica_obj.genero] = [musica_obj]

# dicionário de músicas cujos valores são ordenados por popularidade
musicas = OrderedDict(sorted(musicas_dict.items(),
    key=lambda x: x[1].popularidade, reverse = True))

# para trabalhar melhor com json
generos = list(generos)

# ordena genero_musicas por popularidade
for k,v in genero_musicas.items():
    genero_musicas[k].sort(key = lambda x : x.popularidade, reverse = True)

f.close()

# --- Catálogo de sequências (SQLite) ---
DB_PATH = 'data/sequencias.db'

# As 6 sequências originais, semeadas na criação da tabela (IDs fixos).
SEQUENCIAS_ORIGINAIS = [
    (0, ['Bm', 'G', 'D', 'A']),
    (1, ['C', 'G', 'Am', 'F']),
    (2, ['Em', 'G']),
    (3, ['C', 'A7', 'Dm', 'G7']),
    (4, ['Gm', 'F']),
    (5, ['C', 'C7', 'F', 'Fm']),
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    try:
        with conn:
            conn.execute(
                'CREATE TABLE IF NOT EXISTS sequencias ('
                'id INTEGER PRIMARY KEY, '
                'acordes_json TEXT NOT NULL UNIQUE)'
            )
            for seq_id, acordes_seq in SEQUENCIAS_ORIGINAIS:
                conn.execute(
                    'INSERT OR IGNORE INTO sequencias (id, acordes_json) '
                    'VALUES (?, ?)',
                    (seq_id, json.dumps(acordes_seq))
                )
    finally:
        conn.close()


init_db()


@app.route('/')
def index():
    return app.send_static_file('index.html')
''' Busca por músicas que possuem no título ou no nome do artista o argumento passado por key.
params: key e generos (opcional). Caso generos não sejam definidos, a busca não irá filtrar por gênero.
exemplo 1: /search?key=no dia em que eu saí de casa
exemplo 2: /search?key=no dia em que eu saí de casa&generos=Rock,Samba '''

@app.route('/<path:path>')
def static_proxy(path):
  # send_static_file will guess the correct MIME type
  return app.send_static_file(path)

@app.route('/search')
def busca():
    generos_tag = request.args.get('generos', [])
    pagina_tag = request.args.get('pagina','1')
    keys = request.args.get('key').lower()
    keys = remover_combinantes(keys).split(' ')

    generos_key = generos
    if generos_tag:
        generos_key = generos_tag.split(',')

    collection = apply_filtro(musicas.values(), generos_key)
    out = []

    for musica in collection:
        text = '%s %s' % (musica.nome_artista.lower(), musica.nome_musica.lower())
        text_list = remover_combinantes(text).split(' ')
        if all(key in text_list for key in keys):
            matches = {
                'id_unico_musica' : musica.id_unico_musica,
                'id_artista' : musica.id_artista,
                'id_musica' : musica.id_musica,
                'nome_artista' : musica.nome_artista,
                'nome_musica' : musica.nome_musica,
                'genero' : musica.genero,
                'url' : musica.url,
            }
            out.append(matches)
    return json.dumps(get_pagina(out, pagina_tag))

# cópia
def remover_combinantes(string):
    string = unicodedata.normalize('NFD', string)
    return u''.join(ch for ch in string if unicodedata.category(ch) != 'Mn')

''' Retorna as músicas armazenadas no sistema (ordenados por popularidade).
    O serviço é paginado. Cada página tem tamanho 100, por default.
    params: pagina. Caso não seja definida a página, o valor default é 1.
    exemplo 1: /musica?pagina=2
    exemplo 2: /musica'''
@app.route('/musicas')
def get_musicas():
    return json.dumps([v.__dict__ for v in musicas.values()])

@app.route('/generos')
def get_generos():
    return json.dumps(generos)

@app.route('/acordes')
def get_acordes():
    return json.dumps(list(acordes))

@app.route('/sequencias', methods=['GET'])
def get_sequencias():
    conn = get_db()
    try:
        rows = conn.execute(
            'SELECT id, acordes_json FROM sequencias ORDER BY id'
        ).fetchall()
    finally:
        conn.close()

    return json.dumps([
        {'id': row['id'], 'acordes': json.loads(row['acordes_json'])}
        for row in rows
    ])

@app.route('/sequencias', methods=['POST'])
def criar_sequencia():
    data = request.get_json(silent=True)
    acordes_seq = data.get('acordes') if isinstance(data, dict) else None

    if not isinstance(acordes_seq, list) or len(acordes_seq) == 0:
        return json.dumps({'erro': 'Informe uma lista não vazia de acordes.'}), 400

    if not all(isinstance(a, str) and a.strip() != '' for a in acordes_seq):
        return json.dumps({'erro': 'Acordes inválidos.'}), 400

    acordes_seq = [a.strip() for a in acordes_seq]
    acordes_json = json.dumps(acordes_seq)

    conn = get_db()
    try:
        with conn:
            cur = conn.execute(
                'INSERT INTO sequencias (acordes_json) VALUES (?)',
                (acordes_json,)
            )
            novo_id = cur.lastrowid
    except sqlite3.IntegrityError:
        return json.dumps({'erro': 'Essa sequência já existe.'}), 409
    finally:
        conn.close()

    return json.dumps({'id': novo_id, 'acordes': acordes_seq}), 201

@app.route('/musica/<m_id>/')
def get_musica(m_id):
    return json.dumps(musicas[m_id].__dict__)

@app.route('/similares')
def get_similares():
    # tratando request
    acordes_tag = request.args.get('acordes')
    id_musica_tag = request.args.get('id_unico_musica')
    sequencia_tag = request.args.get('sequencia')
    sequencia_id_tag = request.args.get('sequencia_id')
    pagina_tag = request.args.get('pagina','1')

    # se não existir, filtra por todos.
    generos_tag = request.args.get('generos')
    generos_key = generos
    if generos_tag:
        generos_key = generos_tag.split(',')

    acordes = []
    if acordes_tag:
        acordes = acordes_tag.split(',')
    elif id_musica_tag:
        musica = musicas[id_musica_tag]
        acordes = musica.acordes
    elif sequencia_id_tag or sequencia_tag:
        id_seq = resolve_sequencia_id(sequencia_id_tag, sequencia_tag)
        similares = []

        if id_seq is not None:
            similares = get_pagina(
                get_similares_por_sequencia_custom(id_seq, generos_key),
                pagina_tag
            )
        return json.dumps(similares)

    similares = get_similares(acordes, generos_key, id_musica_tag)

    return json.dumps(get_pagina(similares, pagina_tag))

def resolve_sequencia_id(sequencia_id_tag, sequencia_tag):
    if sequencia_id_tag:
        try:
            return int(sequencia_id_tag)
        except (TypeError, ValueError):
            return None

    if not sequencia_tag:
        return None

    if sequencia_tag.isdigit():
        return int(sequencia_tag)

    # formato legado: lista de acordes separada por vírgula.
    acordes_seq = [a for a in sequencia_tag.split(',') if a != '']
    sequencia = get_sequencia_por_acordes(acordes_seq)
    if sequencia is not None:
        return sequencia['id']
    return None

def get_sequencia_por_id(id_seq):
    conn = get_db()
    try:
        row = conn.execute(
            'SELECT id, acordes_json FROM sequencias WHERE id = ?',
            (id_seq,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    return {'id': row['id'], 'acordes': json.loads(row['acordes_json'])}

def get_sequencia_por_acordes(acordes_seq):
    conn = get_db()
    try:
        row = conn.execute(
            'SELECT id, acordes_json FROM sequencias WHERE acordes_json = ?',
            (json.dumps(acordes_seq),)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    return {'id': row['id'], 'acordes': json.loads(row['acordes_json'])}

def match_contiguo(target_chords, cifra_chords):
    if not target_chords or len(target_chords) > len(cifra_chords):
        return False

    target_len = len(target_chords)
    for i in range(len(cifra_chords) - target_len + 1):
        if cifra_chords[i:i + target_len] == target_chords:
            return True
    return False

def get_similares_por_sequencia_custom(id_seq, generos_key):
    sequencia = get_sequencia_por_id(id_seq)
    if sequencia is None:
        return []

    target_chords = sequencia['acordes']

    # filtra para melhor desempenho
    collection = apply_filtro(musicas.values(), generos_key)

    similares = []
    for musica in collection:
        if match_contiguo(target_chords, musica.cifra):
            similar = {
                'id_unico_musica' : musica.id_unico_musica,
                'id_artista' : musica.id_artista,
                'id_musica' : musica.id_musica,
                'nome_artista' : musica.nome_artista,
                'nome_musica' : musica.nome_musica,
                'popularidade' : musica.popularidade,
                'acordes' : musica.acordes,
                'genero' : musica.genero,
                'url' : musica.url,
            }
            similares.append(similar)

    return similares


def get_pagina(colecao, pagina_tag):
    sl = (int(pagina_tag) - 1)*TAM_PAGINA
    return colecao[sl:sl+TAM_PAGINA]

def get_similares(acordes, generos_key, id_musica = None):

    # filtra para melhor desempenho
    collection = apply_filtro(musicas.values(), generos_key)

    similares = []
    for musica in collection:

        if musica.id_unico_musica != id_musica:

            inter = set(acordes).intersection(set(musica.acordes))
            diff = set(musica.acordes) - set(acordes)

            # somente as que tiverem interseção e as que forem
            # dos generos solicitados.
            if len(inter) > 0:
                similar = {
                        'id_unico_musica' : musica.id_unico_musica,
                        'id_artista' : musica.id_artista,
                        'id_musica' : musica.id_musica,
                        'nome_artista' : musica.nome_artista,
                        'nome_musica' : musica.nome_musica,
                        'popularidade' : musica.popularidade,
                        'acordes' : musica.acordes,
                        'genero' : musica.genero,
                        'url' : musica.url,
                        'diferenca' : list(diff),
                        'intersecao' : list(inter)
                }

                similares.append(similar)

    # ordenados por menor diferença, maior interseção e maior popularidade.
    return sorted(similares, key=lambda x: (len(x['diferenca']), -len(x['intersecao'])))

## Filtra a coleção de músicas por gênero.
def apply_filtro(musicas, generos_key):
    # filtra para melhor desempenho
    collection = []
    for genero in generos_key:
        if genero in generos:
            collection += genero_musicas[genero]
    return collection

@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

if __name__ == '__main__':
    app.run(debug=True)
