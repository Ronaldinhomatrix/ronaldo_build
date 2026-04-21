"""
Painel web do treinador — Ronaldo Medeiros Fisiologista
Roda localmente: python painel/app.py
"""
import csv
import json
import os
import uuid
from datetime import datetime
from functools import wraps

import firebase_admin
from firebase_admin import credentials, firestore
import io

from flask import Flask, redirect, render_template, request, send_file, session, url_for, make_response

# ── Firebase Admin ────────────────────────────────────────────────────────────
# Em produção: variável de ambiente FIREBASE_SA_JSON com o conteúdo do serviceAccount.json
# Em desenvolvimento local: arquivo ../serviceAccount.json

_sa_json = os.environ.get('FIREBASE_SA_JSON')
if _sa_json:
    cred = credentials.Certificate(json.loads(_sa_json))
else:
    _sa_path = os.path.join(os.path.dirname(__file__), '..', 'serviceAccount.json')
    cred = credentials.Certificate(os.path.abspath(_sa_path))

try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ── Flask ─────────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

PAINEL_SENHA = os.environ.get('PAINEL_SENHA', 'admin')


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('autenticado'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def _col():
    return db.collection('atletas')


def _doc(cliente_id):
    return _col().document(cliente_id)


def _col_banco():
    return db.collection('exercicios')


_CATEGORIAS_PADRAO = [
    'Peito', 'Costas', 'Ombros', 'Bíceps', 'Tríceps',
    'Pernas', 'Glúteos', 'Abdômen', 'Cardio', 'Outros',
]


def _carregar_categorias():
    """Retorna lista de categorias (padrão + customizadas), sem duplicatas, ordenada."""
    snap = db.collection('config').document('categorias').get()
    customizadas = snap.to_dict().get('lista', []) if snap.exists else []
    todas = list(dict.fromkeys(_CATEGORIAS_PADRAO + [c for c in customizadas if c not in _CATEGORIAS_PADRAO]))
    return todas


def _adicionar_categoria(nome):
    """Adiciona uma categoria customizada ao Firestore (sem duplicar)."""
    snap = db.collection('config').document('categorias').get()
    atual = snap.to_dict().get('lista', []) if snap.exists else []
    if nome not in _CATEGORIAS_PADRAO and nome not in atual:
        atual.append(nome)
        db.collection('config').document('categorias').set({'lista': atual})


def _carregar_banco():
    return [{'id': d.id, **d.to_dict()} for d in _col_banco().order_by('nome').stream()]


def _proximo_treino(treinos, atividade):
    letras = sorted(treinos.keys())
    if not letras:
        return None
    ultima = {}
    for letra in letras:
        dt_max = None
        for reg in atividade:
            if reg.get('treino') == letra and reg.get('concluido'):
                try:
                    dt = datetime.strptime(
                        f"{reg['data']} {reg['hora']}", '%d/%m/%Y %H:%M:%S'
                    )
                    if dt_max is None or dt > dt_max:
                        dt_max = dt
                except (ValueError, KeyError):
                    pass
        ultima[letra] = dt_max
    if all(v is None for v in ultima.values()):
        return letras[0]
    return min(letras, key=lambda l: ultima[l] or datetime.min)


def _historico_por_exercicio(atividade, filtro='tudo'):
    """
    Agrupa atividade por nome de exercício (ordem A-Z).
    Dentro de cada exercício, sessões do mais recente ao mais antigo.
    filtro: 'semana' (7 dias), 'mes' (30 dias), 'tudo'
    """
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
                if dt < cutoff:
                    continue
            except (ValueError, KeyError):
                pass
        nome = reg.get('nome', '')
        chave = (reg.get('data', ''), reg.get('treino', ''))
        por_exercicio[nome][chave].append(reg)

    resultado = []
    for nome in sorted(por_exercicio.keys()):
        sessoes = []
        for (data, treino), series in sorted(
            por_exercicio[nome].items(),
            key=lambda x: (
                datetime.strptime(x[0][0], '%d/%m/%Y') if x[0][0] else datetime.min
            ),
            reverse=True,
        ):
            series_ord = sorted(series, key=lambda r: r.get('serie', 0))
            feitas   = len(series_ord)
            total    = series_ord[-1].get('series_total', feitas)
            peso     = series_ord[-1].get('peso', '')
            concluido = any(r.get('concluido') for r in series_ord)
            sessoes.append({
                'data':      data,
                'treino':    treino,
                'series':    f'{feitas}/{total}',
                'peso':      peso,
                'concluido': concluido,
            })
        resultado.append({'nome': nome, 'sessoes': sessoes, 'total': len(sessoes)})

    return resultado


def _sessoes_historico(atividade, historico_pesos):
    """
    Agrupa atividade em sessões (data + treino).
    Cada sessão tem lista de exercícios com todas as séries e evolução de carga.
    """
    from collections import defaultdict

    # agrupa por (data, treino)
    grupos = defaultdict(lambda: defaultdict(list))
    for reg in atividade:
        chave = (reg.get('data', ''), reg.get('treino', ''))
        grupos[chave][reg.get('ex_id', '')].append(reg)

    sessoes = []
    for (data, treino), exercicios in sorted(grupos.items(), reverse=True):
        exs = []
        for ex_id, series in exercicios.items():
            series_ord = sorted(series, key=lambda r: r.get('serie', 0))
            nome  = series_ord[-1].get('nome', '')
            peso  = series_ord[-1].get('peso', '')
            total = series_ord[-1].get('series_total', len(series_ord))
            feitas = len(series_ord)
            concluido = any(r.get('concluido') for r in series_ord)
            # evolução de carga deste exercício
            evolucao = historico_pesos.get(ex_id, [])
            exs.append({
                'nome':      nome,
                'series':    f'{feitas}/{total}',
                'peso':      peso,
                'concluido': concluido,
                'evolucao':  sorted(evolucao, key=lambda e: e.get('data', ''), reverse=True),
            })
        sessoes.append({'data': data, 'treino': treino, 'exercicios': exs})

    return sessoes


def _carregar_cliente(cliente_id):
    snap = _doc(cliente_id).get()
    if not snap.exists:
        return None
    d = snap.to_dict()
    treinos         = json.loads(d.get('treinos', '{}'))
    atividade       = json.loads(d.get('atividade', '[]'))
    historico_pesos = json.loads(d.get('historico', '{}'))
    obs_cliente     = d.get('obs_cliente', {}) or {}
    treinos_nomes   = json.loads(d.get('treinos_nomes', '{}'))

    # Mescla obs do cliente nos exercícios pelo ex_id
    for exercicios in treinos.values():
        for ex in exercicios:
            ex['obs'] = obs_cliente.get(ex.get('id', ''), '')

    treino_atual_manual = d.get('treino_atual', '')
    proximo = treino_atual_manual if treino_atual_manual in treinos else _proximo_treino(treinos, atividade)

    return {
        'id':             cliente_id,
        'nome':           d.get('nome', ''),
        'treinos':        treinos,
        'treinos_nomes':  treinos_nomes,
        'historico':      historico_pesos,
        'atividade':      atividade,
        'trainer_editou': d.get('trainer_editou', False),
        'pode_editar':    d.get('pode_editar', True),
        'treino_atual':   treino_atual_manual,
        'proximo_treino': proximo,
        'sessoes':        _sessoes_historico(atividade, historico_pesos),
    }


# ── rotas ─────────────────────────────────────────────────────────────────────

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
    docs = _col().stream()
    clientes = []
    for d in docs:
        data = d.to_dict()
        obs = data.get('obs_cliente', {}) or {}
        # Conta quantas chaves (ID do exercício) têm observação não vazia
        tem_obs = any(v.strip() for v in obs.values()) if obs else False
        
        clientes.append({
            'id':            d.id,
            'nome':          data.get('nome', '(sem nome)'),
            'data_admissao': data.get('data_admissao', ''),
            'tem_obs':       tem_obs
        })

    clientes.sort(key=lambda c: c['nome'])
    return render_template('index.html', clientes=clientes)


@app.route('/exercicios')
@login_required
def banco_exercicios():
    filtro_cat = request.args.get('categoria', '')
    exercicios = _carregar_banco()
    if filtro_cat:
        exercicios = [e for e in exercicios if e.get('categoria', '') == filtro_cat]
    categorias = _carregar_categorias()
    return render_template('exercicios.html', exercicios=exercicios,
                           categorias=categorias, filtro_cat=filtro_cat)


@app.route('/exercicios/categoria/nova', methods=['POST'])
@login_required
def banco_nova_categoria():
    nome = request.form.get('nome', '').strip()
    if nome:
        _adicionar_categoria(nome)
    return redirect(url_for('banco_exercicios'))


@app.route('/exercicios/novo', methods=['POST'])
@login_required
def banco_novo_exercicio():
    nome      = request.form['nome'].strip()
    categoria = request.form.get('categoria', '').strip()
    if nome:
        _col_banco().add({'nome': nome, 'categoria': categoria})
    return redirect(url_for('banco_exercicios'))


@app.route('/exercicios/<ex_id>/editar', methods=['POST'])
@login_required
def banco_editar_exercicio(ex_id):
    nome      = request.form['nome'].strip()
    categoria = request.form.get('categoria', '').strip()
    if nome:
        _col_banco().document(ex_id).update({'nome': nome, 'categoria': categoria})
    return redirect(url_for('banco_exercicios'))


@app.route('/exercicios/<ex_id>/excluir', methods=['POST'])
@login_required
def banco_excluir_exercicio(ex_id):
    _col_banco().document(ex_id).delete()
    return redirect(url_for('banco_exercicios'))


@app.route('/cliente/<cliente_id>')
@login_required
def ver_cliente(cliente_id):
    cliente = _carregar_cliente(cliente_id)
    if cliente is None:
        return 'Cliente não encontrado.', 404
    banco          = _carregar_banco()
    banco_treinos_ = _carregar_banco_treinos()
    categorias     = _carregar_categorias()
    return render_template('atleta.html', cliente=cliente, banco=banco,
                           banco_treinos=banco_treinos_, categorias=categorias)


@app.route('/cliente/<cliente_id>/exercicio/add', methods=['POST'])
@login_required
def add_exercicio(cliente_id):
    treino      = request.form['treino']
    nome        = request.form.get('nome', '').strip()
    series      = request.form.get('series', '').strip()
    repeticoes  = request.form.get('repeticoes', '').strip()
    peso        = request.form.get('peso', '').strip()
    ex_banco_id = request.form.get('ex_banco_id', '').strip()
    obs_trainer = request.form.get('obs_trainer', '').strip()

    if not nome:
        return redirect(url_for('ver_cliente', cliente_id=cliente_id))

    cliente = _carregar_cliente(cliente_id)
    if cliente is None:
        return 'Cliente não encontrado.', 404

    ex = {
        'id': str(uuid.uuid4())[:8], 
        'nome': nome, 
        'series': series,
        'repeticoes': repeticoes, 
        'peso': peso,
        'obs_trainer': obs_trainer
    }
    if ex_banco_id:
        ex['ex_banco_id'] = ex_banco_id

    cliente['treinos'].setdefault(treino, []).append(ex)
    _doc(cliente_id).update({
        'treinos':        json.dumps(cliente['treinos'], ensure_ascii=False),
        'trainer_editou': True,
    })
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))


@app.route('/cliente/<cliente_id>/exercicio/remove', methods=['POST'])
@login_required
def remove_exercicio(cliente_id):
    treino = request.form['treino']
    ex_id  = request.form['ex_id']

    cliente = _carregar_cliente(cliente_id)
    if cliente is None:
        return 'Cliente não encontrado.', 404

    cliente['treinos'][treino] = [
        e for e in cliente['treinos'].get(treino, []) if e['id'] != ex_id
    ]
    _doc(cliente_id).update({
        'treinos':        json.dumps(cliente['treinos'], ensure_ascii=False),
        'trainer_editou': True,
    })
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))


@app.route('/cliente/<cliente_id>/exercicio/edit', methods=['POST'])
@login_required
def edit_exercicio(cliente_id):
    treino     = request.form['treino']
    ex_id      = request.form['ex_id']
    series     = request.form.get('series', '').strip()
    repeticoes = request.form.get('repeticoes', '').strip()
    peso       = request.form.get('peso', '').strip()
    obs_trainer = request.form.get('obs_trainer', '').strip()

    cliente = _carregar_cliente(cliente_id)
    if cliente is None:
        return 'Cliente não encontrado.', 404

    for ex in cliente['treinos'].get(treino, []):
        if ex['id'] == ex_id:
            ex['series']      = series
            ex['repeticoes']  = repeticoes
            ex['peso']        = peso
            ex['obs_trainer'] = obs_trainer
            break
    _doc(cliente_id).update({
        'treinos':        json.dumps(cliente['treinos'], ensure_ascii=False),
        'trainer_editou': True,
    })
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))


@app.route('/cliente/<cliente_id>/excluir', methods=['POST'])
@login_required
def excluir_cliente(cliente_id):
    _doc(cliente_id).delete()
    return redirect(url_for('index'))


@app.route('/cliente/<cliente_id>/pode-editar', methods=['POST'])
@login_required
def toggle_pode_editar(cliente_id):
    cliente = _carregar_cliente(cliente_id)
    if cliente is None:
        return 'Cliente não encontrado.', 404
    novo_valor = not cliente['pode_editar']
    _doc(cliente_id).update({'pode_editar': novo_valor})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))


@app.route('/cliente/<cliente_id>/treino/add', methods=['POST'])
@login_required
def add_treino(cliente_id):
    letras     = ['A', 'B', 'C', 'D', 'E']
    nome_treino = request.form.get('nome_treino', '').strip()
    cliente    = _carregar_cliente(cliente_id)
    existentes = set(cliente['treinos'].keys())
    letra_nova = None
    for letra in letras:
        if letra not in existentes:
            cliente['treinos'][letra] = []
            letra_nova = letra
            break
    if letra_nova and nome_treino:
        cliente['treinos_nomes'][letra_nova] = nome_treino
    _doc(cliente_id).update({
        'treinos':        json.dumps(cliente['treinos'], ensure_ascii=False),
        'treinos_nomes':  json.dumps(cliente['treinos_nomes'], ensure_ascii=False),
        'trainer_editou': True,
    })
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))


@app.route('/cliente/<cliente_id>/treino/definir-atual', methods=['POST'])
@login_required
def definir_treino_atual(cliente_id):
    letra = request.form['letra']
    _doc(cliente_id).update({
        'treino_atual':   letra,
        'trainer_editou': True,
    })
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))


@app.route('/cliente/<cliente_id>/treino/renomear', methods=['POST'])
@login_required
def renomear_treino(cliente_id):
    letra = request.form['letra']
    nome  = request.form.get('nome', '').strip()
    cliente = _carregar_cliente(cliente_id)
    cliente['treinos_nomes'][letra] = nome
    _doc(cliente_id).update({
        'treinos_nomes':  json.dumps(cliente['treinos_nomes'], ensure_ascii=False),
        'trainer_editou': True,
    })
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))


@app.route('/cliente/<cliente_id>/treino/remove', methods=['POST'])
@login_required
def remove_treino(cliente_id):
    letra   = request.form['letra']
    cliente = _carregar_cliente(cliente_id)
    cliente['treinos'].pop(letra, None)
    cliente['treinos_nomes'].pop(letra, None)
    _doc(cliente_id).update({
        'treinos':        json.dumps(cliente['treinos'], ensure_ascii=False),
        'treinos_nomes':  json.dumps(cliente['treinos_nomes'], ensure_ascii=False),
        'trainer_editou': True,
    })
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))


@app.route('/cliente/<cliente_id>/obs/limpar', methods=['POST'])
@login_required
def limpar_obs(cliente_id):
    ex_id = request.form.get('ex_id')
    cliente_snap = _doc(cliente_id).get()
    if not cliente_snap.exists:
        return 'Cliente não encontrado.', 404
    
    dados = cliente_snap.to_dict()
    obs = dados.get('obs_cliente', {}) or {}
    
    if ex_id:
        # Limpa observação de um exercício específico
        obs.pop(ex_id, None)
    else:
        # Limpa todas as observações do cliente
        obs = {}
        
    _doc(cliente_id).update({'obs_cliente': obs})
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))


@app.route('/cliente/<cliente_id>/historico')
@login_required
def historico_cliente(cliente_id):
    filtro  = request.args.get('filtro', 'tudo')
    cliente = _carregar_cliente(cliente_id)
    if cliente is None:
        return 'Cliente não encontrado.', 404
    exercicios = _historico_por_exercicio(cliente['atividade'], filtro)
    return render_template('historico.html', cliente=cliente,
                           exercicios=exercicios, filtro=filtro)


@app.route('/cliente/<cliente_id>/treino/<letra>/exportar')
@login_required
def exportar_treino(cliente_id, letra):
    cliente    = _carregar_cliente(cliente_id)
    exercicios = cliente['treinos'].get(letra, [])
    nome_treino = cliente['treinos_nomes'].get(letra, '')

    dados = {
        'exportado_em': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'nome_treino':  nome_treino,
        'exercicios': [
            {
                'nome':       ex.get('nome', ''),
                'series':     ex.get('series', ''),
                'peso':       ex.get('peso', ''),
                'midia_url':  ex.get('midia_url', ''),
                'midia_tipo': ex.get('midia_tipo', ''),
            }
            for ex in exercicios
        ],
    }
    conteudo     = json.dumps(dados, ensure_ascii=False, indent=2).encode('utf-8')
    nome_cliente = cliente['nome'].replace(' ', '_')
    nome_arquivo = f'treino_{letra}_{nome_cliente}.json'

    return send_file(
        io.BytesIO(conteudo),
        mimetype='application/json',
        as_attachment=True,
        download_name=nome_arquivo,
    )


@app.route('/cliente/<cliente_id>/exportar/completo')
@login_required
def exportar_completo(cliente_id):
    snap = _doc(cliente_id).get()
    if not snap.exists:
        return 'Cliente não encontrado.', 404
    d = snap.to_dict()

    treinos         = json.loads(d.get('treinos', '{}'))
    treinos_nomes   = json.loads(d.get('treinos_nomes', '{}'))
    atividade       = json.loads(d.get('atividade', '[]'))
    historico_pesos = json.loads(d.get('historico', '{}'))
    obs_cliente     = d.get('obs_cliente', {}) or {}

    dados = {
        'exportado_em': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'versao': '1.0',
        'cliente': {
            'nome':         d.get('nome', ''),
            'treino_atual': d.get('treino_atual', ''),
        },
        'treinos': {
            letra: {
                'nome':       treinos_nomes.get(letra, ''),
                'exercicios': exercicios,
            }
            for letra, exercicios in treinos.items()
        },
        'atividade':       atividade,
        'historico_pesos': historico_pesos,
        'obs_cliente':     obs_cliente,
    }

    conteudo = json.dumps(dados, ensure_ascii=False, indent=2).encode('utf-8')
    nome_cliente = d.get('nome', 'cliente').replace(' ', '_')
    nome_arquivo = f'dados_{nome_cliente}_{datetime.now().strftime("%Y%m%d")}.json'

    res = make_response(conteudo)
    res.headers['Content-Disposition'] = f'attachment; filename={nome_arquivo}'
    res.headers['Content-Type']        = 'application/json'
    return res


@app.route('/cliente/<cliente_id>/importar/completo', methods=['POST'])
@login_required
def importar_completo(cliente_id):
    arquivo = request.files.get('arquivo')
    if not arquivo:
        return redirect(url_for('ver_cliente', cliente_id=cliente_id))

    try:
        dados = json.load(arquivo)
        
        # 1. Reconstruir Treinos e Nomes
        novos_treinos = {}
        novos_nomes = {}
        for letra, info in dados.get('treinos', {}).items():
            novos_treinos[letra] = info.get('exercicios', [])
            novos_nomes[letra] = info.get('nome', '')

        # 2. Preparar update
        update_data = {
            'treinos':        json.dumps(novos_treinos, ensure_ascii=False),
            'treinos_nomes':  json.dumps(novos_nomes, ensure_ascii=False),
            'atividade':      json.dumps(dados.get('atividade', []), ensure_ascii=False),
            'historico':      json.dumps(dados.get('historico_pesos', {}), ensure_ascii=False),
            'obs_cliente':    dados.get('obs_cliente', {}),
            'trainer_editou': True
        }

        # 3. Restaurar campos de texto se existirem no backup
        if 'cliente' in dados:
            if dados['cliente'].get('treino_atual'):
                update_data['treino_atual'] = dados['cliente']['treino_atual']

        _doc(cliente_id).update(update_data)
        
    except Exception as e:
        print(f"Erro na importação completa: {e}")
        
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

    return send_file(
        io.BytesIO(conteudo),
        mimetype='application/json',
        as_attachment=True,
        download_name=nome_arquivo,
    )


@app.route('/cliente/<cliente_id>/exportar/progresso')
@login_required
def exportar_progresso(cliente_id):
    cliente = _carregar_cliente(cliente_id)
    if cliente is None:
        return 'Cliente não encontrado.', 404

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['Data', 'Treino', 'Exercício', 'Séries', 'Repetições', 'Carga', 'Concluído'])

    for sessao in cliente['sessoes']:
        for ex in sessao['exercicios']:
            writer.writerow([
                sessao.get('data', ''),
                sessao.get('treino', ''),
                ex.get('nome', ''),
                ex.get('series', ''),
                ex.get('peso', ''),
                'Sim' if ex.get('concluido') else 'Não',
            ])

    conteudo     = buf.getvalue().encode('utf-8-sig')  # utf-8-sig: Excel abre sem problema de acentos
    nome_cliente = cliente['nome'].replace(' ', '_')
    nome_arquivo = f'progresso_{nome_cliente}_{datetime.now().strftime("%Y%m%d")}.csv'

    return send_file(
        io.BytesIO(conteudo),
        mimetype='text/csv',
        as_attachment=True,
        download_name=nome_arquivo,
    )


@app.route('/cliente/<cliente_id>/treino/importar', methods=['POST'])
@login_required
def importar_treino(cliente_id):
    letra   = request.form.get('treino_destino', '').strip()
    arquivo = request.files.get('arquivo')

    if not letra or not arquivo:
        return redirect(url_for('ver_cliente', cliente_id=cliente_id))

    try:
        dados = json.loads(arquivo.read().decode('utf-8'))
    except Exception:
        return 'Arquivo inválido.', 400

    exercicios_importados = dados.get('exercicios', [])
    nome_treino           = dados.get('nome_treino', '')

    cliente = _carregar_cliente(cliente_id)

    novos_exercicios = []
    for ex in exercicios_importados:
        novo = {
            'id':     str(uuid.uuid4()),
            'nome':   ex.get('nome', ''),
            'series': ex.get('series', ''),
            'peso':   ex.get('peso', ''),
        }
        if ex.get('midia_url'):
            novo['midia_url']  = ex['midia_url']
            novo['midia_tipo'] = ex.get('midia_tipo', 'gif')
        novos_exercicios.append(novo)

    cliente['treinos'][letra] = novos_exercicios
    if nome_treino:
        cliente['treinos_nomes'][letra] = nome_treino

    _doc(cliente_id).update({
        'treinos':        json.dumps(cliente['treinos'], ensure_ascii=False),
        'treinos_nomes':  json.dumps(cliente['treinos_nomes'], ensure_ascii=False),
        'trainer_editou': True,
    })
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))


# ── Banco de Treinos ──────────────────────────────────────────────────────────

def _col_banco_treinos():
    return db.collection('banco_treinos')


def _carregar_banco_treinos():
    return [
        {'id': d.id, 'nome': d.to_dict().get('nome', ''),
         'exercicios': json.loads(d.to_dict().get('exercicios', '[]'))}
        for d in _col_banco_treinos().order_by('nome').stream()
    ]


def _carregar_template(template_id):
    snap = _col_banco_treinos().document(template_id).get()
    if not snap.exists:
        return None
    d = snap.to_dict()
    return {
        'id':         template_id,
        'nome':       d.get('nome', ''),
        'exercicios': json.loads(d.get('exercicios', '[]')),
    }


@app.route('/banco-treinos')
@login_required
def banco_treinos():
    templates = _carregar_banco_treinos()
    return render_template('banco_treinos.html', templates=templates)


@app.route('/banco-treinos/novo', methods=['POST'])
@login_required
def banco_treinos_novo():
    nome = request.form.get('nome', '').strip()
    if nome:
        _col_banco_treinos().add({'nome': nome, 'exercicios': '[]'})
    return redirect(url_for('banco_treinos'))


@app.route('/banco-treinos/<template_id>')
@login_required
def banco_treino_detalhe(template_id):
    template = _carregar_template(template_id)
    if template is None:
        return 'Template não encontrado.', 404
    banco      = _carregar_banco()
    categorias = _carregar_categorias()
    return render_template('banco_treino_detalhe.html', template=template,
                           banco=banco, categorias=categorias)


@app.route('/banco-treinos/<template_id>/renomear', methods=['POST'])
@login_required
def banco_treino_renomear(template_id):
    nome = request.form.get('nome', '').strip()
    if nome:
        _col_banco_treinos().document(template_id).update({'nome': nome})
    return redirect(url_for('banco_treino_detalhe', template_id=template_id))


@app.route('/banco-treinos/<template_id>/excluir', methods=['POST'])
@login_required
def banco_treino_excluir(template_id):
    _col_banco_treinos().document(template_id).delete()
    return redirect(url_for('banco_treinos'))


@app.route('/banco-treinos/<template_id>/exercicio/add', methods=['POST'])
@login_required
def banco_treino_add_ex(template_id):
    template = _carregar_template(template_id)
    if template is None:
        return 'Template não encontrado.', 404
    nome       = request.form.get('nome', '').strip()
    series     = request.form.get('series', '').strip()
    repeticoes = request.form.get('repeticoes', '').strip()
    peso       = request.form.get('peso', '').strip()
    if nome:
        ex = {'id': str(uuid.uuid4()), 'nome': nome, 'series': series,
              'repeticoes': repeticoes, 'peso': peso}
        template['exercicios'].append(ex)
        _col_banco_treinos().document(template_id).update(
            {'exercicios': json.dumps(template['exercicios'], ensure_ascii=False)}
        )
    return redirect(url_for('banco_treino_detalhe', template_id=template_id))


@app.route('/banco-treinos/<template_id>/exercicio/edit', methods=['POST'])
@login_required
def banco_treino_edit_ex(template_id):
    template = _carregar_template(template_id)
    if template is None:
        return 'Template não encontrado.', 404
    ex_id      = request.form.get('ex_id', '')
    series     = request.form.get('series', '').strip()
    repeticoes = request.form.get('repeticoes', '').strip()
    peso       = request.form.get('peso', '').strip()
    for ex in template['exercicios']:
        if ex['id'] == ex_id:
            ex['series']     = series
            ex['repeticoes'] = repeticoes
            ex['peso']       = peso
            break
    _col_banco_treinos().document(template_id).update(
        {'exercicios': json.dumps(template['exercicios'], ensure_ascii=False)}
    )
    return redirect(url_for('banco_treino_detalhe', template_id=template_id))


@app.route('/banco-treinos/<template_id>/exercicio/remove', methods=['POST'])
@login_required
def banco_treino_remove_ex(template_id):
    template = _carregar_template(template_id)
    if template is None:
        return 'Template não encontrado.', 404
    ex_id = request.form.get('ex_id', '')
    template['exercicios'] = [e for e in template['exercicios'] if e['id'] != ex_id]
    _col_banco_treinos().document(template_id).update(
        {'exercicios': json.dumps(template['exercicios'], ensure_ascii=False)}
    )
    return redirect(url_for('banco_treino_detalhe', template_id=template_id))


@app.route('/cliente/<cliente_id>/treino/<letra>/aplicar-template', methods=['POST'])
@login_required
def aplicar_template(cliente_id, letra):
    template_id = request.form.get('template_id', '').strip()
    template = _carregar_template(template_id)
    if template is None:
        return 'Template não encontrado.', 404
    cliente = _carregar_cliente(cliente_id)
    if cliente is None:
        return 'Cliente não encontrado.', 404
    novos = [
        {**{k: v for k, v in ex.items() if k != 'id'}, 'id': str(uuid.uuid4())}
        for ex in template['exercicios']
    ]
    cliente['treinos'][letra] = novos
    _doc(cliente_id).update({
        'treinos':        json.dumps(cliente['treinos'], ensure_ascii=False),
        'trainer_editou': True,
    })
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))


@app.route('/notificar-obs', methods=['POST'])
def notificar_obs():
    # Fallback para o token padrão caso a variável de ambiente não esteja definida
    token = os.environ.get('NOTIF_TOKEN', 'notif2024!')
    if request.headers.get('X-Token') != token:
        return 'Não autorizado.', 403

    dados = request.get_json(silent=True) or {}
    cliente_nome = dados.get('cliente_nome', 'Cliente')
    ex_nome      = dados.get('ex_nome', 'exercício')
    obs_texto    = dados.get('obs', '')

    _enviar_telegram_obs(cliente_nome, ex_nome, obs_texto)
    return 'ok', 200


def _enviar_telegram_obs(cliente_nome, ex_nome, obs_texto):
    token   = os.environ.get('TELEGRAM_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        return

    import urllib.request as _req
    texto = (
        f'📋 *Nova observação*\n'
        f'Cliente: *{cliente_nome}*\n'
        f'Exercício: *{ex_nome}*\n'
        f'Obs: {obs_texto}'
    )
    body = json.dumps({
        'chat_id':    chat_id,
        'text':       texto,
        'parse_mode': 'Markdown',
    }).encode('utf-8')
    req = _req.Request(
        f'https://api.telegram.org/bot{token}/sendMessage',
        data=body,
        headers={'Content-Type': 'application/json'},
    )
    try:
        _req.urlopen(req, timeout=10)
    except Exception as e:
        print(f'[Telegram] erro ao enviar: {e}')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
