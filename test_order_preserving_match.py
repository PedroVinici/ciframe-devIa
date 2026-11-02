#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste de algoritmo alternativo para match de sequências de acordes
preservando ordem e repetições.

Ideia: ao invés de usar interseção de conjuntos (Musica.acordes),
usar Musica.cifra (lista ordenada/limpa) e buscar se a sequência
alvo aparece como subsequência (preservando ordem, permitindo repetições)
dentro da cifra da música.

Para validação inicial, compara com o resultado atual via seqs_famosas
para as 6 sequências hardcoded em main.sequencias.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main


SEQUENCIAS_HARDCODED = {
    'BmGDA': 0,
    'CGAmF': 1,
    'EmG': 2,
    'CA7DmG7': 3,
    'GmF': 4,
    'CC7FFm': 5,
}


# Mapeamento dos nomes sem vírgula para os acordes (conforme frontend/backend)
SEQUENCIA_TO_CHORDS = {
    'BmGDA': ['Bm', 'G', 'D', 'A'],
    'CGAmF': ['C', 'G', 'Am', 'F'],
    'EmG': ['Em', 'G'],
    'CA7DmG7': ['C', 'A7', 'Dm', 'G7'],
    'GmF': ['Gm', 'F'],
    'CC7FFm': ['C', 'C7', 'F', 'Fm'],
}


def get_musicas_by_seqs_famosas(id_seq):
    """Obtém músicas que têm o id_seq em seqs_famosas (mesmo critério atual)."""
    result = []
    for musica in main.musicas.values():
        if str(id_seq) in musica.seqs_famosas:
            result.append(musica)
    return result


def match_contiguous_sequence(target_chords, cifra_chords):
    """
    Verifica se target_chords aparece como sequência CONTÍGUA em cifra_chords,
    preservando ordem e repetições (não usa set).
    
    Acordes no meio da sequência alvo NÃO são permitidos.
    Os acordes devem aparecer consecutivamente na cifra.
    """
    if not target_chords:
        return False
    if len(target_chords) > len(cifra_chords):
        return False
    
    # Busca target_chords como bloco contíguo
    target_len = len(target_chords)
    for i in range(len(cifra_chords) - target_len + 1):
        if cifra_chords[i : i + target_len] == target_chords:
            return True
    return False


def get_musicas_by_order_preserving_match(target_chords, generos_key=None):
    """
    Versão alternativa similar à lógica de get_similares/get_similares_por_sequencia,
    mas usando Musica.cifra (preservando ordem/repetições) ao invés de sets/tags.
    Busca por sequência CONTÍGUA (sem acordes no meio).
    """
    if generos_key is None:
        generos_key = main.generos
    
    # Aplica filtro por gênero (mesma lógica)
    collection = main.apply_filtro(main.musicas.values(), generos_key)
    
    similares = []
    for musica in collection:
        if match_contiguous_sequence(target_chords, musica.cifra):
            similar = {
                'id_unico_musica': musica.id_unico_musica,
                'id_artista': musica.id_artista,
                'id_musica': musica.id_musica,
                'nome_artista': musica.nome_artista,
                'nome_musica': musica.nome_musica,
                'popularidade': musica.popularidade,
                'acordes': musica.acordes,
                'cifra_len': len(musica.cifra),
                'genero': musica.genero,
                'url': musica.url,
            }
            similares.append(similar)
    
    return similares, collection


def test_all_hardcoded_sequences():
    print("=" * 80)
    print("TESTE: Comparação entre algoritmo atual (seqs_famosas) vs novo (match CONTÍGUO em Musica.cifra)")
    print("=" * 80)
    print()
    
    all_passed = True
    
    for seq_name, seq_id in sorted(SEQUENCIAS_HARDCODED.items(), key=lambda x: x[1]):
        target_chords = SEQUENCIA_TO_CHORDS[seq_name]
        
        # Resultado atual
        current_musicas = get_musicas_by_seqs_famosas(seq_id)
        current_ids = set(m.id_unico_musica for m in current_musicas)
        
        # Novo algoritmo
        new_musicas, _ = get_musicas_by_order_preserving_match(target_chords)
        new_ids = set(m['id_unico_musica'] for m in new_musicas)
        
        # Comparação: novo deve conter pelo menos todas as músicas marcadas com tag
        missing = current_ids - new_ids
        is_superset = len(missing) == 0
        if not is_superset:
            all_passed = False
        
        print(f"Sequência: {seq_name} (id={seq_id}) | Alvo: {' -> '.join(target_chords)}")
        print(f"  Atual (seqs_famosas): {len(current_ids)} músicas")
        print(f"  Novo (subsequência em cifra): {len(new_ids)} músicas")
        print(f"  Contém todas as tags: {is_superset} (faltando: {len(missing)})")
        print(f"  Novas encontradas: {len(new_ids - current_ids)}")
        
        if missing:
            print(f"  Apenas no atual (não encontradas pelo novo): {list(missing)[:5]}")
        
        print()
    
    print("=" * 80)
    if all_passed:
        print("✓ TODOS OS TESTES PASSARAM - Resultados idênticos!")
    else:
        print("✗ ALGUNS TESTES FALHARAM - Há diferenças nos resultados")
    print("=" * 80)
    
    return all_passed


def test_with_comma_format():
    """Testa com formato como vem do frontend (com vírgulas)"""
    print("\n" + "=" * 80)
    print("TESTE: Formato com vírgulas (como frontend envia)")
    print("=" * 80)
    print()
    
    for seq_name, seq_id in sorted(SEQUENCIAS_HARDCODED.items(), key=lambda x: x[1]):
        target_chords = SEQUENCIA_TO_CHORDS[seq_name]
        target_comma = ','.join(target_chords)
        
        # Simula como backend recebe
        acordes_clean = target_comma.replace(',', '')
        # Verifica se está nas chaves hardcoded
        if acordes_clean in main.sequencias:
            current_count = len(get_musicas_by_seqs_famosas(seq_id))
        else:
            current_count = 0
        
        new_musicas, _ = get_musicas_by_order_preserving_match(target_chords)
        
        print(f"{seq_name} ({target_comma}): atual={current_count}, novo={len(new_musicas)}")
    
    print("=" * 80)


if __name__ == '__main__':
    try:
        passed = test_all_hardcoded_sequences()
        test_with_comma_format()
        sys.exit(0 if passed else 1)
    except Exception as e:
        print(f"ERRO: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
