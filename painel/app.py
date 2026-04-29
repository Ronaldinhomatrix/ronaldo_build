"""
Painel web do treinador — Ronaldo Medeiros Fisiologista
Versão: 3.3 - Restauração Completa de Rotas
"""
import csv
import json
import os
import uuid
import io
from datetime import datetime
from functools import wraps
from flask import Flask, redirect, render_template, request, send_file, session, url_for, make_response
import firebase_admin
from firebase_admin import credentials, firestore

# ── Firebase Admin ────────────────────────────────────────────────────────────
_sa_json = os.environ.get('FIREBASE_SA_JSON')
if _sa_json:
    try:
        info = json.loads(_sa_json)
        cred = credentials.Certificate(info)
    except Exception as e:
        print(f"Erro FIREBASE_SA_JSON: {e}")
        _sa_path = os.path.join(os.path.dirname(__file__), '..', 'serviceAccount.json')
        cred = credentials.Certificate(os.path.abspath(_sa_path))
else:
    _sa_path = os.path.join(os.path.dirname(__file__), '..', 'serviceAccount.json')
    cred = credentials.Certificate(os.path.abspath(_sa_path)) if os.path.exists(_sa_path) else None

if cred:
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    db = None

# ── Flask ─────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_123')
PAINEL_SENHA = os.environ.get('PAINEL_SENHA', 'admin')

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('autenticado'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def _col(): return db.collection('atletas')
def _doc(cid): return _col().document(cid)
def _col_banco(): return db.collection('exercicios')
def _col_banco_treinos(): return db.collection('banco_treinos')

def _safe_json(val, default):
    if not val: return default
    if isinstance(val, (dict, list)): return val
    try: return json.loads(val)
    except: return default

_CATEGORIAS_PADRAO = ['Peito', 'Costas', 'Ombros', 'Bíceps', 'Tríceps', 'Pernas', 'Glúteos', 'Abdômen', 'Cardio', 'Outros']

def _carregar_categorias():
    try:
        snap = db.collection('config').document('categorias').get()
        custom = snap.to_dict().get('lista', []) if snap.exists else []
        return list(dict.fromkeys(_CATEGORIAS_PADRAO + custom))
    except: return _CATEGORIAS_PADRAO

def _carregar_banco():
    return [{'id': d.id, **d.to_dict()} for d in _col_banco().order_by('nome').stream()]

def _carregar_banco_treinos():
    return [{'id': d.id, 'nome': d.to_dict().get('nome', ''), 'exercicios': _safe_json(d.to_dict().get('exercicios'), [])} for d in _col_banco_treinos().order_by('nome').stream()]

def _carregar_template(template_id):
    snap = _col_banco_treinos().document(template_id).get()
    if not snap.exists: return None
    d = snap.to_dict()
    return {'id': template_id, 'nome': d.get('nome', ''), 'exercicios': _safe_json(d.get('exercicios'), [])}

def _carregar_cliente(cliente_id):
    snap = _doc(cliente_id).get()
    if not snap.exists: return None
    d = snap.to_dict()
    treinos = _safe_json(d.get('treinos'), {})
    atividade = _safe_json(d.get('atividade'), [])
    historico_pesos = _safe_json(d.get('historico'), {})
    obs_cliente = d.get('obs_cliente', {})
    if not isinstance(obs_cliente, dict): obs_cliente = {}
    
    if isinstance(treinos, dict):
        for exercicios in treinos.values():
            if isinstance(exercicios, list):
                for ex in exercicios:
                    if isinstance(ex, dict):
                        ex['obs'] = obs_cliente.get(ex.get('id', ''), '')

    return {
        'id': cliente_id,
        'nome': d.get('nome', ''),
        'treinos': treinos,
        'treinos_nomes': _safe_json(d.get('treinos_nomes'), {}),
        'historico': historico_pesos,
        'atividade': atividade,
        'trainer_editou': d.get('trainer_editou', False),
        'pode_editar': d.get('pode_editar', True),
        'treino_atual': d.get('treino_atual', ''),
        'obs_cliente': obs_cliente,
        'sessoes': _sessoes_historico(atividade, historico_pesos),
    }

def _sessoes_historico(atividade, historico_pesos):
    from collections import defaultdict
    grupos = defaultdict(lambda: defaultdict(list))
    for reg in atividade:
        chave = (reg.get('data', ''), reg.get('treino', ''))
        grupos[chave][reg.get('ex_id', '')].append(reg)
    sessoes = []
    for (data, treino), exercicios in sorted(grupos.items(), reverse=True):
        exs = []
        for ex_id, series in exercicios.items():
            series_ord = sorted(series, key=lambda r: r.get('serie', 0))
            exs.append({
                'nome': series_ord[-1].get('nome', ''),
                'series': f"{len(series_ord)}/{series_ord[-1].get('series_total', len(series_ord))}",
                'peso': series_ord[-1].get('peso', ''),
                'concluido': any(r.get('concluido') for r in series_ord),
            })
        sessoes.append({'data': data, 'treino': treino, 'exercicios': exs})
    return sessoes

# ── Rotas ─────────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        if request.form.get('senha') == PAINEL_SENHA:
            session['autenticado'] = True
            return redirect(url_for('index'))
        erro = 'Senha incorreta.'
    return render_template('login.html', erro=erro)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    if db is None: return "Erro de conexão com Firebase. Verifique FIREBASE_SA_JSON.", 500
    try:
        docs = _col().stream()
        clientes = []
        for d in docs:
            data = d.to_dict()
            obs = data.get('obs_cliente', {})
            tem_obs = False
            if isinstance(obs, dict):
                tem_obs = any(str(v).strip() for v in obs.values() if v)
            clientes.append({
                'id': d.id,
                'nome': data.get('nome', '(sem nome)'),
                'data_admissao': data.get('data_admissao', ''),
                'tem_obs': tem_obs
            })
        clientes.sort(key=lambda c: c['nome'])
        return render_template('index.html', clientes=clientes)
    except Exception as e:
        return f"Erro ao carregar lista: {e}", 500

@app.route('/exercicios')
@login_required
def banco_exercicios():
    exercicios = _carregar_banco()
    categorias = _carregar_categorias()
    return render_template('exercicios.html', exercicios=exercicios, categorias=categorias, filtro_cat='')

@app.route('/cliente/<cliente_id>')
@login_required
def ver_cliente(cliente_id):
    cliente = _carregar_cliente(cliente_id)
    if not cliente: return 'Cliente não encontrado.', 404
    banco = _carregar_banco()
    banco_treinos = _carregar_banco_treinos()
    categorias = _carregar_categorias()
    return render_template('atleta.html', cliente=cliente, banco=banco, banco_treinos=banco_treinos, categorias=categorias)

@app.route('/cliente/<cliente_id>/exercicio/add', methods=['POST'])
@login_required
def add_exercicio(cliente_id):
    treino = request.form['treino']
    nome = request.form.get('nome', '').strip()
    if not nome: return redirect(url_for('ver_cliente', cliente_id=cliente_id))
    cliente = _carregar_cliente(cliente_id)
    ex = {
        'id': str(uuid.uuid4())[:8], 
        'nome': nome, 
        'series': request.form.get('series', ''),
        'repeticoes': request.form.get('repeticoes', ''), 
        'peso': request.form.get('peso', ''),
        'obs_trainer': request.form.get('obs_trainer', '').strip()
    }
    cliente['treinos'].setdefault(treino, []).append(ex)
    _doc(cliente_id).update({'treinos': json.dumps(cliente['treinos'], ensure_ascii=False), 'trainer_editou': True})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

@app.route('/cliente/<cliente_id>/exercicio/remove', methods=['POST'])
@login_required
def remove_exercicio(cliente_id):
    treino = request.form['treino']
    ex_id = request.form['ex_id']
    cliente = _carregar_cliente(cliente_id)
    cliente['treinos'][treino] = [e for e in cliente['treinos'].get(treino, []) if e['id'] != ex_id]
    _doc(cliente_id).update({'treinos': json.dumps(cliente['treinos'], ensure_ascii=False), 'trainer_editou': True})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

@app.route('/banco-treinos')
@login_required
def banco_treinos():
    templates = _carregar_banco_treinos()
    return render_template('banco_treinos.html', templates=templates)

@app.route('/notificar-obs', methods=['POST'])
def notificar_obs():
    token = os.environ.get('NOTIF_TOKEN', 'notif2024!')
    if request.headers.get('X-Token') != token: return 'Não autorizado.', 403
    dados = request.get_json(silent=True) or {}
    _enviar_telegram_obs(dados.get('cliente_nome', 'Cliente'), dados.get('ex_nome', 'exercício'), dados.get('obs', ''))
    return 'ok', 200

def _enviar_telegram_obs(cliente, ex, obs):
    token = os.environ.get('TELEGRAM_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id: return
    import urllib.request as _req
    texto = f'📋 Nova observação\nCliente: {cliente}\nExercício: {ex}\nObs: {obs}'
    body = json.dumps({'chat_id': chat_id, 'text': texto}).encode('utf-8')
    req = _req.Request(f'https://api.telegram.org/bot{token}/sendMessage', data=body, headers={'Content-Type': 'application/json'})
    try: _req.urlopen(req, timeout=15)
    except: pass

if __name__ == '__main__':
    app.run(debug=True, port=5000)
