"""
Sincronização com o Firebase Firestore via REST API.
Todas as chamadas de rede rodam em threads de background — o app nunca trava.
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

_BASE = (
    f'https://firestore.googleapis.com/v1/'
    f'projects/{PROJECT_ID}/databases/(default)/documents'
)


# ── conversão Python ↔ Firestore ──────────────────────────────────────────────

def _para_fs(valor):
    if isinstance(valor, bool):
        return {'booleanValue': valor}
    if isinstance(valor, int):
        return {'integerValue': str(valor)}
    if isinstance(valor, float):
        return {'doubleValue': valor}
    if isinstance(valor, str):
        return {'stringValue': valor}
    if isinstance(valor, dict):
        return {'mapValue': {'fields': {k: _para_fs(v) for k, v in valor.items()}}}
    if isinstance(valor, list):
        return {'arrayValue': {'values': [_para_fs(v) for v in valor]}}
    return {'nullValue': None}


def _de_fs(fv):
    if 'stringValue'  in fv: return fv['stringValue']
    if 'booleanValue' in fv: return fv['booleanValue']
    if 'integerValue' in fv: return int(fv['integerValue'])
    if 'doubleValue'  in fv: return fv['doubleValue']
    if 'nullValue'    in fv: return None
    if 'mapValue'     in fv:
        return {k: _de_fs(v) for k, v in fv['mapValue'].get('fields', {}).items()}
    if 'arrayValue'   in fv:
        return [_de_fs(v) for v in fv['arrayValue'].get('values', [])]
    return None


# ── helpers HTTP ──────────────────────────────────────────────────────────────

def _patch(path, fields):
    """PATCH com updateMask — atualiza apenas os campos informados."""
    mask = '&'.join(f'updateMask.fieldPaths={k}' for k in fields)
    url  = f'{_BASE}/{path}?key={API_KEY}&{mask}'
    body = json.dumps({'fields': fields}).encode('utf-8')
    req  = urllib.request.Request(url, data=body, method='PATCH')
    req.add_header('Content-Type', 'application/json')
    urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT)


def _get(path):
    url = f'{_BASE}/{path}?key={API_KEY}'
    with urllib.request.urlopen(url, timeout=15, context=_SSL_CONTEXT) as resp:
        return json.loads(resp.read())


def buscar_id_por_nome(nome):
    """
    Pesquisa no Firestore se já existe um atleta com este nome.
    Retorna o ID do documento se encontrar, ou None se for novo.
    """
    try:
        # Query via REST API
        url = f'https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents:runQuery?key={API_KEY}'
        query = {
            "structuredQuery": {
                "from": [{"collectionId": "atletas"}],
                "where": {
                    "fieldFilter": {
                        "field": {"fieldPath": "nome"},
                        "op": "EQUAL",
                        "value": {"stringValue": nome}
                    }
                },
                "limit": 1
            }
        }
        body = json.dumps(query).encode('utf-8')
        req = urllib.request.Request(url, data=body, method='POST')
        req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CONTEXT) as resp:
            resultados = json.loads(resp.read())
            # O Firestore retorna uma lista. Se o primeiro item tiver um 'document', ele existe.
            if resultados and 'document' in resultados[0]:
                path = resultados[0]['document']['name']
                return path.split('/')[-1] # Retorna apenas o ID (final do caminho)
    except Exception as e:
        print(f'[Firebase] Erro ao buscar por nome: {e}')
    return None


# ── API pública ───────────────────────────────────────────────────────────────

def criar_cliente(cliente_id, nome):
    """Cria o documento do cliente no Firestore (background)."""
    def _run():
        try:
            _patch(f'atletas/{cliente_id}', {
                'nome':           _para_fs(nome),
                'treinos':        _para_fs(json.dumps({}, ensure_ascii=False)),
                'historico':      _para_fs('{}'),
                'atividade':      _para_fs('[]'),
                'obs_cliente':    _para_fs({}),
                'trainer_editou': _para_fs(False),
                'data_admissao':  _para_fs(datetime.now().strftime('%d/%m/%Y')),
            })
        except Exception as e:
            print(f'[Firebase] criar_cliente: {e}')
    threading.Thread(target=_run, daemon=True).start()


def salvar_dados(cliente_id, historico, atividade, obs_cliente=None, on_success=None, on_error=None):
    """
    Envia historico, atividade e obs do cliente ao Firestore (background).
    NÃO envia treinos — treinos são controlados exclusivamente pelo painel.
    """
    def _run():
        from kivy.clock import Clock
        try:
            fields = {
                'historico':      _para_fs(json.dumps(historico, ensure_ascii=False)),
                'atividade':      _para_fs(json.dumps(atividade, ensure_ascii=False)),
                'trainer_editou': _para_fs(False),
            }
            if obs_cliente is not None:
                fields['obs_cliente'] = _para_fs(obs_cliente)
            _patch(f'atletas/{cliente_id}', fields)
            if on_success:
                Clock.schedule_once(lambda dt: on_success(), 0)
        except Exception as e:
            print(f'[Firebase] salvar_dados: {e}')
            if on_error:
                Clock.schedule_once(lambda dt: on_error(str(e)), 0)
    threading.Thread(target=_run, daemon=True).start()


def salvar_atividade(cliente_id, atividade, on_error=None):
    """
    Envia apenas o campo 'atividade' ao Firestore (background).
    Chamado a cada série registrada. Se falhar, chama on_error() para retry posterior.
    """
    def _run():
        try:
            _patch(f'atletas/{cliente_id}', {
                'atividade': _para_fs(json.dumps(atividade, ensure_ascii=False)),
            })
        except Exception as e:
            print(f'[Firebase] salvar_atividade: {e}')
            if on_error:
                on_error()
    threading.Thread(target=_run, daemon=True).start()


def buscar_cliente_completo(cliente_id):
    """
    Busca todos os dados do cliente (síncrono — chame em thread separada).
    Retorna dict com chaves: treinos, trainer_editou, pode_editar, obs_cliente
    — ou None em caso de erro.
    """
    try:
        doc    = _get(f'atletas/{cliente_id}')
        fields = doc.get('fields', {})
        treinos_json       = _de_fs(fields.get('treinos',        {'stringValue': '{}'}))
        treinos_nomes_json = _de_fs(fields.get('treinos_nomes',  {'stringValue': '{}'}))
        trainer_editou     = _de_fs(fields.get('trainer_editou', {'booleanValue': False}))
        pode_editar        = _de_fs(fields.get('pode_editar',    {'booleanValue': True}))
        treino_atual       = _de_fs(fields.get('treino_atual',   {'stringValue': ''}))
        obs_raw            = fields.get('obs_cliente', {'mapValue': {'fields': {}}})
        obs_cliente        = _de_fs(obs_raw) or {}
        return {
            'treinos':        json.loads(treinos_json),
            'treinos_nomes':  json.loads(treinos_nomes_json),
            'trainer_editou': trainer_editou,
            'pode_editar':    pode_editar,
            'treino_atual':   treino_atual,
            'obs_cliente':    obs_cliente,
        }
    except Exception as e:
        print(f'[Firebase] buscar_cliente_completo: {e}')
        return None


def notificar_obs(cliente_nome, ex_nome, obs_texto, on_success=None, on_error=None, retentativas=3):
    """
    Avisa o treinador sobre nova observação do cliente (background).
    Tenta automaticamente 'retentativas' vezes em caso de timeout/erro.
    """
    def _run():
        from kivy.clock import Clock
        import time
        
        for tentativa in range(retentativas):
            try:
                from firebase_config import PAINEL_URL, NOTIF_TOKEN
                url  = f'{PAINEL_URL}/notificar-obs'
                body = json.dumps({
                    'cliente_nome': cliente_nome,
                    'ex_nome':      ex_nome,
                    'obs':          obs_texto,
                }).encode('utf-8')
                req = urllib.request.Request(
                    url, data=body,
                    headers={
                        'Content-Type': 'application/json',
                        'X-Token':      NOTIF_TOKEN,
                        'User-Agent':   'RonaldoApp/2.8'
                    },
                )
                # Timeout menor por tentativa para não demorar demais no total
                urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT)
                
                if on_success:
                    Clock.schedule_once(lambda dt: on_success(), 0)
                return  # Sucesso! Sai da função.

            except Exception as err:
                erro_msg = str(err)
                print(f'[Notif] Tentativa {tentativa + 1} falhou: {erro_msg}')
                if tentativa < retentativas - 1:
                    time.sleep(2)
                else:
                    if on_error:
                        # Capturamos erro_msg em uma variável local para o lambda
                        Clock.schedule_once(lambda dt, m=erro_msg: on_error(m), 0)

    threading.Thread(target=_run, daemon=True).start()


def limpar_treino_atual(cliente_id):
    """Remove o override manual de treino_atual após o cliente concluir aquele treino."""
    def _run():
        try:
            _patch(f'atletas/{cliente_id}', {'treino_atual': _para_fs('')})
        except Exception as e:
            print(f'[Firebase] limpar_treino_atual: {e}')
    threading.Thread(target=_run, daemon=True).start()


def marcar_trainer_lido(cliente_id):
    """Reseta trainer_editou=False após o cliente puxar as mudanças (background)."""
    def _run():
        try:
            _patch(f'atletas/{cliente_id}', {'trainer_editou': _para_fs(False)})
        except Exception as e:
            print(f'[Firebase] marcar_trainer_lido: {e}')
    threading.Thread(target=_run, daemon=True).start()
