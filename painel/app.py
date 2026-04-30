"""
Painel web do treinador — Ronaldo Medeiros Fisiologista
Versão: 3.5 - RESTAURAÇÃO ABSOLUTA (Histórico, Progresso, Backup, Exclusão)
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
app.secret_key = os.environ.get('SECRET_KEY', 'ronaldo_secret_key_fixed_999')
PAINEL_SENHA = os.environ.get('PAINEL_SENHA', 'admin')
_CATEGORIAS_PADRAO = ['Peito', 'Costas', 'Ombros', 'Bíceps', 'Tríceps', 'Pernas', 'Glúteos', 'Abdômen', 'Cardio', 'Outros']

# ── Helpers de Segurança e Dados ──────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('autenticado'): return redirect(url_for('login'))
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

def _historico_por_exercicio(atividade, filtro='tudo'):
    from collections import defaultdict
    cutoff = None
    if filtro in ('semana', 'mes'):
        from datetime import timedelta
        dias = 7 if filtro == 'semana' else 30
        cutoff = datetime.now() - timedelta(days=dias)
    por_exercicio = defaultdict(lambda: defaultdict(list))
    for reg in atividade:
        if cutoff:
            try:
                dt = datetime.strptime(reg['data'], '%d/%m/%Y')
                if dt < cutoff: continue
            except: pass
        nome = reg.get('nome', '')
        chave = (reg.get('data', ''), reg.get('treino', ''))
        por_exercicio[nome][chave].append(reg)
    resultado = []
    for nome in sorted(por_exercicio.keys()):
        sessoes = []
        for (data, treino), series in sorted(por_exercicio[nome].items(), key=lambda x: (datetime.strptime(x[0][0], '%d/%m/%Y') if x[0][0] else datetime.min), reverse=True):
            series_ord = sorted(series, key=lambda r: r.get('serie', 0))
            sessoes.append({
                'data': data, 'treino': treino, 'series': f'{len(series_ord)}/{series_ord[-1].get("series_total", len(series_ord))}',
                'peso': series_ord[-1].get('peso', ''), 'concluido': any(r.get('concluido') for r in series_ord)
            })
        resultado.append({'nome': nome, 'sessoes': sessoes, 'total': len(sessoes)})
    return resultado

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
                    if isinstance(ex, dict): ex['obs'] = obs_cliente.get(ex.get('id', ''), '')
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
    if db is None: return "Erro de conexão com Firebase.", 500
    try:
        docs = _col().stream()
        clientes = []
        for d in docs:
            data = d.to_dict()
            obs = data.get('obs_cliente', {})
            tem_obs = any(str(v).strip() for v in obs.values() if v) if isinstance(obs, dict) else False
            clientes.append({'id': d.id, 'nome': data.get('nome', '(sem nome)'), 'data_admissao': data.get('data_admissao', ''), 'tem_obs': tem_obs})
        clientes.sort(key=lambda c: c['nome'])
        return render_template('index.html', clientes=clientes)
    except Exception as e: return f"Erro: {e}", 500

@app.route('/cliente/<cliente_id>')
@login_required
def ver_cliente(cliente_id):
    cliente = _carregar_cliente(cliente_id)
    if not cliente: return 'Cliente não encontrado.', 404
    return render_template('atleta.html', cliente=cliente, banco=_carregar_banco(), banco_treinos=_carregar_banco_treinos(), categorias=_carregar_categorias())

@app.route('/cliente/<cliente_id>/excluir', methods=['POST'])
@login_required
def excluir_cliente(cliente_id):
    _doc(cliente_id).delete()
    return redirect(url_for('index'))

@app.route('/cliente/<cliente_id>/historico')
@login_required
def historico_cliente(cliente_id):
    filtro = request.args.get('filtro', 'tudo')
    cliente = _carregar_cliente(cliente_id)
    if not cliente: return 'Erro', 404
    return render_template('historico.html', cliente=cliente, exercicios=_historico_por_exercicio(cliente['atividade'], filtro), filtro=filtro)

@app.route('/cliente/<cliente_id>/exportar/progresso')
@login_required
def exportar_progresso(cliente_id):
    cliente = _carregar_cliente(cliente_id)
    if not cliente: return 'Erro', 404
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['Data', 'Treino', 'Exercício', 'Séries', 'Carga', 'Concluído'])
    for sessao in cliente['sessoes']:
        for ex in sessao['exercicios']:
            writer.writerow([sessao.get('data',''), sessao.get('treino',''), ex.get('nome',''), ex.get('series',''), ex.get('peso',''), 'Sim' if ex.get('concluido') else 'Não'])
    res = make_response(buf.getvalue().encode('utf-8-sig'))
    res.headers['Content-Disposition'] = f'attachment; filename=progresso_{cliente["nome"]}.csv'
    res.headers['Content-Type'] = 'text/csv'
    return res

@app.route('/cliente/<cliente_id>/exportar/completo')
@login_required
def exportar_completo(cliente_id):
    snap = _doc(cliente_id).get()
    if not snap.exists: return 'Erro', 404
    d = snap.to_dict()
    dados = {'exportado_em': datetime.now().strftime('%d/%m/%Y %H:%M'), 'cliente': {'nome': d.get('nome', '')}, 'treinos': _safe_json(d.get('treinos'), {}), 'atividade': _safe_json(d.get('atividade'), []), 'historico_pesos': _safe_json(d.get('historico'), {}), 'obs_cliente': d.get('obs_cliente', {})}
    res = make_response(json.dumps(dados, ensure_ascii=False, indent=2))
    res.headers['Content-Disposition'] = f'attachment; filename=backup_{d.get("nome","cliente")}.json'
    res.headers['Content-Type'] = 'application/json'
    return res

@app.route('/cliente/<cliente_id>/importar/completo', methods=['POST'])
@login_required
def importar_completo(cliente_id):
    arquivo = request.files.get('arquivo')
    if arquivo:
        try:
            dados = json.load(arquivo)
            _doc(cliente_id).update({'treinos': json.dumps(dados.get('treinos',{}), ensure_ascii=False), 'atividade': json.dumps(dados.get('atividade',[]), ensure_ascii=False), 'historico': json.dumps(dados.get('historico_pesos',{}), ensure_ascii=False), 'obs_cliente': dados.get('obs_cliente', {}), 'trainer_editou': True})
        except: pass
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

# ── Outras Rotas (Exercícios, Treinos, etc) ──────────────────────────────────

@app.route('/cliente/<cliente_id>/exercicio/add', methods=['POST'])
@login_required
def add_exercicio(cliente_id):
    treino = request.form['treino']
    nome = request.form.get('nome', '').strip()
    if not nome: return redirect(url_for('ver_cliente', cliente_id=cliente_id))
    cliente = _carregar_cliente(cliente_id)
    ex = {'id': str(uuid.uuid4())[:8], 'nome': nome, 'series': request.form.get('series', ''), 'repeticoes': request.form.get('repeticoes', ''), 'peso': request.form.get('peso', ''), 'obs_trainer': request.form.get('obs_trainer', '').strip()}
    cliente['treinos'].setdefault(treino, []).append(ex)
    _doc(cliente_id).update({'treinos': json.dumps(cliente['treinos'], ensure_ascii=False), 'trainer_editou': True})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

@app.route('/cliente/<cliente_id>/exercicio/edit', methods=['POST'])
@login_required
def edit_exercicio(cliente_id):
    treino, ex_id = request.form['treino'], request.form['ex_id']
    cliente = _carregar_cliente(cliente_id)
    for ex in cliente['treinos'].get(treino, []):
        if ex['id'] == ex_id:
            ex['series'], ex['repeticoes'], ex['peso'], ex['obs_trainer'] = request.form.get('series',''), request.form.get('repeticoes',''), request.form.get('peso',''), request.form.get('obs_trainer','')
            break
    _doc(cliente_id).update({'treinos': json.dumps(cliente['treinos'], ensure_ascii=False), 'trainer_editou': True})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

@app.route('/cliente/<cliente_id>/exercicio/remove', methods=['POST'])
@login_required
def remove_exercicio(cliente_id):
    treino, ex_id = request.form['treino'], request.form['ex_id']
    cliente = _carregar_cliente(cliente_id)
    cliente['treinos'][treino] = [e for e in cliente['treinos'].get(treino, []) if e['id'] != ex_id]
    _doc(cliente_id).update({'treinos': json.dumps(cliente['treinos'], ensure_ascii=False), 'trainer_editou': True})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

@app.route('/cliente/<cliente_id>/treino/add', methods=['POST'])
@login_required
def add_treino(cliente_id):
    letras, cliente = ['A', 'B', 'C', 'D', 'E'], _carregar_cliente(cliente_id)
    for letra in letras:
        if letra not in cliente['treinos']:
            cliente['treinos'][letra] = []
            if request.form.get('nome_treino'): cliente['treinos_nomes'][letra] = request.form.get('nome_treino')
            break
    _doc(cliente_id).update({'treinos': json.dumps(cliente['treinos'], ensure_ascii=False), 'treinos_nomes': json.dumps(cliente['treinos_nomes'], ensure_ascii=False), 'trainer_editou': True})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

@app.route('/cliente/<cliente_id>/obs/limpar', methods=['POST'])
@login_required
def limpar_obs(cliente_id):
    ex_id = request.form.get('ex_id')
    cliente_snap = _doc(cliente_id).get()
    obs = cliente_snap.to_dict().get('obs_cliente', {}) if cliente_snap.exists else {}
    if not isinstance(obs, dict): obs = {}
    if ex_id: obs.pop(ex_id, None)
    else: obs = {}
    _doc(cliente_id).update({'obs_cliente': obs, 'trainer_editou': True})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

@app.route('/exercicios')
@login_required
def banco_exercicios():
    return render_template('exercicios.html', exercicios=_carregar_banco(), categorias=_carregar_categorias(), filtro_cat='')

@app.route('/banco-treinos')
@login_required
def banco_treinos():
    return render_template('banco_treinos.html', templates=_carregar_banco_treinos())

@app.route('/notificar-obs', methods=['POST'])
def notificar_obs():
    token = os.environ.get('NOTIF_TOKEN', 'notif2024!')
    if request.headers.get('X-Token') != token: return 'Erro', 403
    dados = request.get_json(silent=True) or {}
    token_tg, chat_id = os.environ.get('TELEGRAM_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if token_tg and chat_id:
        import urllib.request as _req
        texto = f'📋 Nova observação\nCliente: {dados.get("cliente_nome")}\nEx: {dados.get("ex_nome")}\nObs: {dados.get("obs")}'
        try: _req.urlopen(_req.Request(f'https://api.telegram.org/bot{token_tg}/sendMessage', data=json.dumps({'chat_id': chat_id, 'text': texto}).encode('utf-8'), headers={'Content-Type': 'application/json'}), timeout=10)
        except: pass
    return 'ok', 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
