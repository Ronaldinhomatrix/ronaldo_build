"""
Painel web do treinador — Ronaldo Medeiros Fisiologista
Versão: 3.4 - RESTAURAÇÃO INTEGRAL DE TODAS AS FUNÇÕES
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

# ── Flask e Configurações ─────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ronaldo_secret_key_fixed')
PAINEL_SENHA = os.environ.get('PAINEL_SENHA', 'admin')

_CATEGORIAS_PADRAO = ['Peito', 'Costas', 'Ombros', 'Bíceps', 'Tríceps', 'Pernas', 'Glúteos', 'Abdômen', 'Cardio', 'Outros']

# ── Helpers de Segurança e Dados ──────────────────────────────────────────────

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
    try:
        if isinstance(val, str): return json.loads(val)
    except: pass
    return default

def _proximo_treino(treinos, atividade):
    letras = sorted(treinos.keys())
    if not letras: return None
    ultima = {}
    for letra in letras:
        dt_max = None
        for reg in atividade:
            if reg.get('treino') == letra and reg.get('concluido'):
                try:
                    dt = datetime.strptime(f"{reg['data']} {reg['hora']}", '%d/%m/%Y %H:%M:%S')
                    if dt_max is None or dt > dt_max: dt_max = dt
                except: pass
        ultima[letra] = dt_max
    if all(v is None for v in ultima.values()): return letras[0]
    return min(letras, key=lambda l: ultima[l] or datetime.min)

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

    treino_atual_manual = d.get('treino_atual', '')
    proximo = treino_atual_manual if treino_atual_manual in treinos else _proximo_treino(treinos, atividade)

    return {
        'id': cliente_id, 'nome': d.get('nome', ''), 'treinos': treinos,
        'treinos_nomes': _safe_json(d.get('treinos_nomes'), {}),
        'historico': historico_pesos, 'atividade': atividade,
        'trainer_editou': d.get('trainer_editou', False), 'pode_editar': d.get('pode_editar', True),
        'treino_atual': treino_atual_manual, 'proximo_treino': proximo,
        'obs_cliente': obs_cliente, 'sessoes': _sessoes_historico(atividade, historico_pesos),
    }

# ── Rotas Principais ──────────────────────────────────────────────────────────

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
                'id': d.id, 'nome': data.get('nome', '(sem nome)'),
                'data_admissao': data.get('data_admissao', ''), 'tem_obs': tem_obs
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
    return render_template('atleta.html', cliente=cliente, banco=_carregar_banco(),
                           banco_treinos=_carregar_banco_treinos(), categorias=_carregar_categorias())

# ── Gestão de Exercícios do Cliente ──────────────────────────────────────────

@app.route('/cliente/<cliente_id>/exercicio/add', methods=['POST'])
@login_required
def add_exercicio(cliente_id):
    treino = request.form['treino']
    nome = request.form.get('nome', '').strip()
    if not nome: return redirect(url_for('ver_cliente', cliente_id=cliente_id))
    cliente = _carregar_cliente(cliente_id)
    ex = {
        'id': str(uuid.uuid4())[:8], 'nome': nome, 
        'series': request.form.get('series', ''), 'repeticoes': request.form.get('repeticoes', ''), 
        'peso': request.form.get('peso', ''), 'obs_trainer': request.form.get('obs_trainer', '').strip()
    }
    cliente['treinos'].setdefault(treino, []).append(ex)
    _doc(cliente_id).update({'treinos': json.dumps(cliente['treinos'], ensure_ascii=False), 'trainer_editou': True})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

@app.route('/cliente/<cliente_id>/exercicio/edit', methods=['POST'])
@login_required
def edit_exercicio(cliente_id):
    treino = request.form['treino']
    ex_id = request.form['ex_id']
    cliente = _carregar_cliente(cliente_id)
    for ex in cliente['treinos'].get(treino, []):
        if ex['id'] == ex_id:
            ex['series'] = request.form.get('series', '').strip()
            ex['repeticoes'] = request.form.get('repeticoes', '').strip()
            ex['peso'] = request.form.get('peso', '').strip()
            ex['obs_trainer'] = request.form.get('obs_trainer', '').strip()
            break
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

# ── Gestão de Treinos (A,B,C...) ─────────────────────────────────────────────

@app.route('/cliente/<cliente_id>/treino/add', methods=['POST'])
@login_required
def add_treino(cliente_id):
    letras = ['A', 'B', 'C', 'D', 'E']
    cliente = _carregar_cliente(cliente_id)
    for letra in letras:
        if letra not in cliente['treinos']:
            cliente['treinos'][letra] = []
            nome = request.form.get('nome_treino', '').strip()
            if nome: cliente['treinos_nomes'][letra] = nome
            break
    _doc(cliente_id).update({'treinos': json.dumps(cliente['treinos'], ensure_ascii=False),
                             'treinos_nomes': json.dumps(cliente['treinos_nomes'], ensure_ascii=False), 'trainer_editou': True})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

@app.route('/cliente/<cliente_id>/treino/renomear', methods=['POST'])
@login_required
def renomear_treino(cliente_id):
    letra = request.form['letra']
    nome = request.form.get('nome', '').strip()
    cliente = _carregar_cliente(cliente_id)
    cliente['treinos_nomes'][letra] = nome
    _doc(cliente_id).update({'treinos_nomes': json.dumps(cliente['treinos_nomes'], ensure_ascii=False), 'trainer_editou': True})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

@app.route('/cliente/<cliente_id>/treino/remove', methods=['POST'])
@login_required
def remove_treino(cliente_id):
    letra = request.form['letra']
    cliente = _carregar_cliente(cliente_id)
    cliente['treinos'].pop(letra, None)
    cliente['treinos_nomes'].pop(letra, None)
    _doc(cliente_id).update({'treinos': json.dumps(cliente['treinos'], ensure_ascii=False),
                             'treinos_nomes': json.dumps(cliente['treinos_nomes'], ensure_ascii=False), 'trainer_editou': True})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

@app.route('/cliente/<cliente_id>/treino/definir-atual', methods=['POST'])
@login_required
def definir_treino_atual(cliente_id):
    _doc(cliente_id).update({'treino_atual': request.form['letra'], 'trainer_editou': True})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

# ── Observações e Permissões ─────────────────────────────────────────────────

@app.route('/cliente/<cliente_id>/obs/limpar', methods=['POST'])
@login_required
def limpar_obs(cliente_id):
    ex_id = request.form.get('ex_id')
    cliente_snap = _doc(cliente_id).get()
    if not cliente_snap.exists: return 'Erro', 404
    obs = cliente_snap.to_dict().get('obs_cliente', {})
    if not isinstance(obs, dict): obs = {}
    if ex_id: obs.pop(ex_id, None)
    else: obs = {}
    _doc(cliente_id).update({'obs_cliente': obs, 'trainer_editou': True})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

@app.route('/cliente/<cliente_id>/pode-editar', methods=['POST'])
@login_required
def toggle_pode_editar(cliente_id):
    cliente = _carregar_cliente(cliente_id)
    _doc(cliente_id).update({'pode_editar': not cliente['pode_editar']})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

# ── Banco de Exercícios Geral ────────────────────────────────────────────────

@app.route('/exercicios')
@login_required
def banco_exercicios():
    return render_template('exercicios.html', exercicios=_carregar_banco(), categorias=_carregar_categorias(), filtro_cat='')

@app.route('/exercicios/novo', methods=['POST'])
@login_required
def banco_novo_exercicio():
    nome = request.form['nome'].strip()
    if nome: _col_banco().add({'nome': nome, 'categoria': request.form.get('categoria', '').strip()})
    return redirect(url_for('banco_exercicios'))

@app.route('/exercicios/<ex_id>/excluir', methods=['POST'])
@login_required
def banco_excluir_exercicio(ex_id):
    _col_banco().document(ex_id).delete()
    return redirect(url_for('banco_exercicios'))

@app.route('/exercicios/categoria/nova', methods=['POST'])
@login_required
def banco_nova_categoria():
    nome = request.form.get('nome', '').strip()
    if nome:
        snap = db.collection('config').document('categorias').get()
        atual = snap.to_dict().get('lista', []) if snap.exists else []
        if nome not in atual:
            atual.append(nome)
            db.collection('config').document('categorias').set({'lista': atual})
    return redirect(url_for('banco_exercicios'))

# ── Banco de Treinos (Templates) ─────────────────────────────────────────────

@app.route('/banco-treinos')
@login_required
def banco_treinos():
    return render_template('banco_treinos.html', templates=_carregar_banco_treinos())

@app.route('/banco-treinos/novo', methods=['POST'])
@login_required
def banco_treinos_novo():
    nome = request.form.get('nome', '').strip()
    if nome: _col_banco_treinos().add({'nome': nome, 'exercicios': '[]'})
    return redirect(url_for('banco_treinos'))

@app.route('/cliente/<cliente_id>/treino/<letra>/aplicar-template', methods=['POST'])
@login_required
def aplicar_template(cliente_id, letra):
    template = _carregar_template(request.form.get('template_id'))
    if template:
        novos = [{**{k: v for k, v in ex.items() if k != 'id'}, 'id': str(uuid.uuid4())[:8]} for ex in template['exercicios']]
        cliente = _carregar_cliente(cliente_id)
        cliente['treinos'][letra] = novos
        _doc(cliente_id).update({'treinos': json.dumps(cliente['treinos'], ensure_ascii=False), 'trainer_editou': True})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

# ── Exportação e Telegram ────────────────────────────────────────────────────

@app.route('/notificar-obs', methods=['POST'])
def notificar_obs():
    token = os.environ.get('NOTIF_TOKEN', 'notif2024!')
    if request.headers.get('X-Token') != token: return 'Não autorizado.', 403
    dados = request.get_json(silent=True) or {}
    _enviar_telegram_obs(dados.get('cliente_nome', 'Cliente'), dados.get('ex_nome', 'exercício'), dados.get('obs', ''))
    return 'ok', 200

def _enviar_telegram_obs(cliente, ex, obs):
    token, chat_id = os.environ.get('TELEGRAM_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id: return
    import urllib.request as _req
    texto = f'📋 Nova observação\nCliente: {cliente}\nExercício: {ex}\nObs: {obs}'
    try:
        body = json.dumps({'chat_id': chat_id, 'text': texto}).encode('utf-8')
        req = _req.Request(f'https://api.telegram.org/bot{token}/sendMessage', data=body, headers={'Content-Type': 'application/json'})
        _req.urlopen(req, timeout=15)
    except: pass

if __name__ == '__main__':
    app.run(debug=True, port=5000)
