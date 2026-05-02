"""
Sincronização com o Firebase Firestore via biblioteca Requests.
Versão: 3.2 - Busca via Query EQUAL (Correção do Erro 400).
"""
import json
import threading
from datetime import datetime
import requests

from firebase_config import API_KEY, PROJECT_ID

_BASE = f'https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents'
_HEADERS = {'User-Agent': 'RonaldoMedeirosApp/3.17'}

# ── Conversão Firestore ──────────────────────────────────────────────────────

def _de_fs(fv):
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
    if isinstance(valor, bool): return {'booleanValue': valor}
    if isinstance(valor, int): return {'integerValue': str(valor)}
    if isinstance(valor, float): return {'doubleValue': valor}
    if isinstance(valor, str): return {'stringValue': valor}
    if isinstance(valor, dict): return {'mapValue': {'fields': {k: _para_fs(v) for k, v in valor.items()}}}
    if isinstance(valor, list): return {'arrayValue': {'values': [_para_fs(v) for v in valor]}}
    return {'nullValue': None}

# ── API Pública ───────────────────────────────────────────────────────────────

def buscar_cliente_completo(cliente_id):
    """
    Busca dados via runQuery com caminho completo (EQUAL) para evitar 400/403.
    """
    try:
        url = f'{_BASE}:runQuery'
        params = {'key': API_KEY}
        
        # O Firestore exige o caminho completo para filtrar pelo nome do documento (__name__)
        caminho_completo = f'projects/{PROJECT_ID}/databases/(default)/documents/atletas/{cliente_id}'
        
        query = {
            "structuredQuery": {
                "from": [{"collectionId": "atletas"}],
                "where": {
                    "fieldFilter": {
                        "field": {"fieldPath": "__name__"},
                        "op": "EQUAL",
                        "value": {"referenceValue": caminho_completo}
                    }
                },
                "limit": 1
            }
        }
        resp = requests.post(url, params=params, json=query, headers=_HEADERS, timeout=15)
        
        if resp.status_code == 200:
            res_json = resp.json()
            if not res_json or 'document' not in res_json[0]:
                return {'status': 'nao_encontrado'}
                
            doc = res_json[0]['document']
            fields = doc.get('fields', {})
            
            # Decodifica treinos
            t_raw = _de_fs(fields.get('treinos'))
            treinos = json.loads(t_raw) if isinstance(t_raw, str) else (t_raw or {})
            
            n_raw = _de_fs(fields.get('treinos_nomes'))
            nomes = json.loads(n_raw) if isinstance(n_raw, str) else (n_raw or {})

            return {
                'treinos': treinos,
                'treinos_nomes': nomes,
                'trainer_editou': _de_fs(fields.get('trainer_editou')) or False,
                'treino_atual': _de_fs(fields.get('treino_atual')) or '',
                'status': 'sucesso'
            }
        else:
            return {'status': f'erro_{resp.status_code}'}
    except Exception as e:
        print(f"Erro Sync: {e}")
        return {'status': 'offline'}

def buscar_id_por_nome(nome):
    try:
        url = f'{_BASE}:runQuery'
        params = {'key': API_KEY}
        query = {"structuredQuery": {"from": [{"collectionId": "atletas"}], "where": {"fieldFilter": {"field": {"fieldPath": "nome"}, "op": "EQUAL", "value": {"stringValue": nome}}}, "limit": 1}}
        resp = requests.post(url, params=params, json=query, headers=_HEADERS, timeout=10)
        if resp.status_code == 200:
            res = resp.json()
            if res and 'document' in res[0]:
                return res[0]['document']['name'].split('/')[-1]
    except: pass
    return None

def criar_cliente(cliente_id, nome):
    def _run():
        try:
            url = f'{_BASE}/atletas/{cliente_id}'
            params = {'key': API_KEY}
            data = {'fields': {
                'nome': _para_fs(nome),
                'treinos': _para_fs('{}'),
                'historico': _para_fs('{}'),
                'atividade': _para_fs('[]'),
                'obs_cliente': _para_fs({}),
                'trainer_editou': _para_fs(False),
                'data_admissao': _para_fs(datetime.now().strftime('%d/%m/%Y')),
            }}
            requests.patch(url, params=params, json=data, headers=_HEADERS, timeout=10)
        except: pass
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
            requests.patch(url, json={'fields': fields}, headers=_HEADERS, timeout=15)
            if on_success: Clock.schedule_once(lambda dt: on_success(), 0)
        except Exception as e:
            if on_error: Clock.schedule_once(lambda dt: on_error(str(e)), 0)
    threading.Thread(target=_run, daemon=True).start()
