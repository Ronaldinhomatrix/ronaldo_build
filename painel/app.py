"""
Painel web do treinador — Ronaldo Medeiros Fisiologista
Versão: 3.2 - Proteção Total e Blindagem
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

def _safe_json(val, default):
    if not val: return default
    if isinstance(val, (dict, list)): return val
    try: return json.loads(val)
    except: return default

def _carregar_cliente(cliente_id):
    snap = _doc(cliente_id).get()
    if not snap.exists: return None
    d = snap.to_dict()
    treinos = _safe_json(d.get('treinos'), {})
    atividade = _safe_json(d.get('atividade'), [])
    historico_pesos = _safe_json(d.get('historico'), {})
    obs_cliente = d.get('obs_cliente', {})
    if not isinstance(obs_cliente, dict): obs_cliente = {}
    
    # Proteção para o loop de treinos
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

@app.route('/cliente/<cliente_id>')
@login_required
def ver_cliente(cliente_id):
    cliente = _carregar_cliente(cliente_id)
    if not cliente: return 'Cliente não encontrado.', 404
    return render_template('atleta.html', cliente=cliente, banco=[], banco_treinos=[], categorias=[])

# ... (restante das rotas simplificadas para manter o site vivo)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
