"""
Sincronização com o Firebase Firestore via REST API.
Versão: 2.0 - Robusta para tipos de dados variados.
"""
import json
import ssl
import threading
import urllib.error
import urllib.request
from datetime import datetime

from firebase_config import API_KEY, PROJECT_ID

try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL_CONTEXT = ssl.create_default_context()

_BASE = f'https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents'

# ── Conversão Robusta ────────────────────────────────────────────────────────

def _de_fs(fv):
    """Converte valores do formato Firestore para Python (robusto)."""
    if not fv or not isinstance(fv, dict): return None
    if 'stringValue'  in fv: return fv['stringValue']
    if 'booleanValue' in fv: return fv['booleanValue']
    if 'integerValue' in fv: return int(fv['integerValue'])
    if 'doubleValue'  in fv: return fv['doubleValue']
    if 'mapValue'     in fv:
        return {k: _de_fs(v) for k, v in fv['mapValue'].get('fields', {}).items()}
    if 'arrayValue'   in fv:
        return [_de_fs(v) for v in fv['arrayValue'].get('values', [])]
    return None

def _para_fs(valor):
    """Converte Python para formato Firestore."""
    if isinstance(valor, bool): return {'booleanValue': valor}
    if isinstance(valor, int): return {'integerValue': str(valor)}
    if isinstance(valor, float): return {'doubleValue': valor}
    if isinstance(valor, str): return {'stringValue': valor}
    if isinstance(valor, dict): return {'mapValue': {'fields': {k: _para_fs(v) for k, v in valor.items()}}}
    if isinstance(valor, list): return {'arrayValue': {'values': [_para_fs(v) for v in valor]}}
    return {'nullValue': None}

# ── API Pública ───────────────────────────────────────────────────────────────

def buscar_cliente_completo(cliente_id):
    """Busca dados do cliente, aceitando treinos como String JSON ou Mapa Direto."""
    try:
        url = f'{_BASE}/atletas/{cliente_id}?key={API_KEY}'
        with urllib.request.urlopen(url, timeout=15, context=_SSL_CONTEXT) as resp:
            doc = json.loads(resp.read())
            fields = doc.get('fields', {})
            
            # Treinos: pode vir como String (velho) ou Mapa (novo)
            treinos_raw = _de_fs(fields.get('treinos'))
            if isinstance(treinos_raw, str): treinos = json.loads(treinos_raw)
            elif isinstance(treinos_raw, dict): treinos = treinos_raw
            else: treinos = {}

            # Nomes: mesma lógica
            nomes_raw = _de_fs(fields.get('treinos_nomes'))
            if isinstance(nomes_raw, str): nomes = json.loads(nomes_raw)
            elif isinstance(nomes_raw, dict): nomes = nomes_raw
            else: nomes = {}

            return {
                'treinos': treinos,
                'treinos_nomes': nomes,
                'trainer_editou': _de_fs(fields.get('trainer_editou')) or False,
                'pode_editar': _de_fs(fields.get('pode_editar')) if 'pode_editar' in fields else True,
                'treino_atual': _de_fs(fields.get('treino_atual')) or '',
                'obs_cliente': _de_fs(fields.get('obs_cliente')) or {},
            }
    except Exception as e:
        print(f'[Firebase] Erro ao buscar: {e}')
        return None

def criar_cliente(cliente_id, nome):
    def _run():
        try:
            url = f'{_BASE}/atletas/{cliente_id}?key={API_KEY}'
            body = json.dumps({'fields': {
                'nome': _para_fs(nome),
                'treinos': _para_fs('{}'),
                'historico': _para_fs('{}'),
                'atividade': _para_fs('[]'),
                'obs_cliente': _para_fs({}),
                'trainer_editou': _para_fs(False),
                'data_admissao': _para_fs(datetime.now().strftime('%d/%m/%Y')),
            }}).encode('utf-8')
            req = urllib.request.Request(url, data=body, method='PATCH')
            req.add_header('Content-Type', 'application/json')
            urllib.request.urlopen(req, timeout=10, context=_SSL_CONTEXT)
        except Exception as e: print(f'[Firebase] Criar: {e}')
    threading.Thread(target=_run, daemon=True).start()

def salvar_dados(cliente_id, historico, atividade, obs_cliente=None, on_success=None, on_error=None):
    def _run():
        from kivy.clock import Clock
        try:
            fields = {
                'historico': _para_fs(json.dumps(historico, ensure_ascii=False)),
                'atividade': _para_fs(json.dumps(atividade, ensure_ascii=False)),
                'trainer_editou': _para_fs(False),
            }
            if obs_cliente: fields['obs_cliente'] = _para_fs(obs_cliente)
            
            mask = '&'.join(f'updateMask.fieldPaths={k}' for k in fields.keys())
            url = f'{_BASE}/atletas/{cliente_id}?key={API_KEY}&{mask}'
            req = urllib.request.Request(url, data=json.dumps({'fields': fields}).encode('utf-8'), method='PATCH')
            req.add_header('Content-Type', 'application/json')
            urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT)
            if on_success: Clock.schedule_once(lambda dt: on_success(), 0)
        except Exception as e:
            if on_error: Clock.schedule_once(lambda dt: on_error(str(e)), 0)
    threading.Thread(target=_run, daemon=True).start()

def buscar_id_por_nome(nome):
    """
    Busca o ID do cliente no Firestore.
    Rigor absoluto: exige correspondência exata de caracteres.
    """
    try:
        url = f'{_BASE}:runQuery?key={API_KEY}'
        # A query EQUAL do Firestore é sensível a maiúsculas/minúsculas por padrão
        query = {"structuredQuery": {"from": [{"collectionId": "atletas"}], "where": {"fieldFilter": {"field": {"fieldPath": "nome"}, "op": "EQUAL", "value": {"stringValue": nome}}}, "limit": 1}}
        req = urllib.request.Request(url, data=json.dumps(query).encode('utf-8'), method='POST')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CONTEXT) as resp:
            res = json.loads(resp.read())
            if res and 'document' in res[0]:
                return res[0]['document']['name'].split('/')[-1]
    except: pass
    return None

def notificar_obs(cliente_nome, ex_nome, obs_texto, on_success=None, on_error=None):
    def _run():
        from kivy.clock import Clock
        try:
            from firebase_config import PAINEL_URL, NOTIF_TOKEN
            body = json.dumps({'cliente_nome': cliente_nome, 'ex_nome': ex_nome, 'obs': obs_texto}).encode('utf-8')
            req = urllib.request.Request(f'{PAINEL_URL}/notificar-obs', data=body, headers={'Content-Type': 'application/json', 'X-Token': NOTIF_TOKEN})
            urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT)
            if on_success: Clock.schedule_once(lambda dt: on_success(), 0)
        except Exception as e:
            if on_error: Clock.schedule_once(lambda dt: on_error(str(e)), 0)
    threading.Thread(target=_run, daemon=True).start()
