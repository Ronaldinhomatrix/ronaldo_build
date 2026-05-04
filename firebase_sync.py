"""
Sincronização com o Firebase Firestore.
Versão: 3.19 - Retorno ao motor urllib original.
"""
import json
import ssl
import threading
import urllib.request
from datetime import datetime
from firebase_config import API_KEY, PROJECT_ID

try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except:
    _SSL_CONTEXT = ssl.create_default_context()

_BASE = f'https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents'

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

def buscar_cliente_completo(cliente_id):
    try:
        url = f'{_BASE}/atletas/{cliente_id}?key={API_KEY}'
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT) as resp:
            doc = json.loads(resp.read())
            fields = doc.get('fields', {})
            t_raw = _de_fs(fields.get('treinos'))
            treinos = json.loads(t_raw) if isinstance(t_raw, str) else (t_raw or {})
            n_raw = _de_fs(fields.get('treinos_nomes'))
            nomes = json.loads(n_raw) if isinstance(n_raw, str) else (n_raw or {})
            return {
                'treinos': treinos, 'treinos_nomes': nomes,
                'trainer_editou': _de_fs(fields.get('trainer_editou')) or False,
                'treino_atual': _de_fs(fields.get('treino_atual')) or '',
                'status': 'sucesso'
            }
    except Exception as e:
        err_msg = str(e)
        if '403' in err_msg: return {'status': 'erro_403', 'mensagem': err_msg}
        if '404' in err_msg: return {'status': 'erro_404', 'mensagem': "Cliente não encontrado no banco"}
        return {'status': 'erro', 'mensagem': err_msg}

def buscar_id_por_nome(nome):
    try:
        url = f'{_BASE}:runQuery?key={API_KEY}'
        query = {"structuredQuery": {"from": [{"collectionId": "atletas"}], "where": {"fieldFilter": {"field": {"fieldPath": "nome"}, "op": "EQUAL", "value": {"stringValue": nome}}}, "limit": 1}}
        body = json.dumps(query).encode('utf-8')
        req = urllib.request.Request(url, data=body, method='POST')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CONTEXT) as resp:
            res = json.loads(resp.read())
            if res and 'document' in res[0]: return res[0]['document']['name'].split('/')[-1]
    except: pass
    return None

def criar_cliente(cliente_id, nome):
    def _run():
        try:
            url = f'{_BASE}/atletas/{cliente_id}?key={API_KEY}'
            fields = {'nome': {'stringValue': nome}, 'treinos': {'stringValue': '{}'}, 'trainer_editou': {'booleanValue': False}, 'data_admissao': {'stringValue': datetime.now().strftime('%d/%m/%Y')}}
            body = json.dumps({'fields': fields}).encode('utf-8')
            req = urllib.request.Request(url, data=body, method='PATCH')
            req.add_header('Content-Type', 'application/json')
            urllib.request.urlopen(req, timeout=10, context=_SSL_CONTEXT)
        except: pass
    threading.Thread(target=_run, daemon=True).start()

def salvar_dados(cliente_id, historico, atividade, obs_cliente=None, on_success=None, on_error=None):
    def _run():
        from kivy.clock import Clock
        try:
            fields = {'historico': {'stringValue': json.dumps(historico)}, 'atividade': {'stringValue': json.dumps(atividade)}, 'trainer_editou': {'booleanValue': False}}
            mask = 'updateMask.fieldPaths=historico&updateMask.fieldPaths=atividade&updateMask.fieldPaths=trainer_editou'
            url = f'{_BASE}/atletas/{cliente_id}?key={API_KEY}&{mask}'
            req = urllib.request.Request(url, data=json.dumps({'fields': fields}).encode('utf-8'), method='PATCH')
            req.add_header('Content-Type', 'application/json')
            urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT)
            if on_success: Clock.schedule_once(lambda dt: on_success(), 0)
        except Exception as e:
            if on_error: Clock.schedule_once(lambda dt: on_error(str(e)), 0)
    threading.Thread(target=_run, daemon=True).start()
