import json
import os
import platform
import threading
import uuid
from datetime import datetime

from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivymd.app import MDApp

import firebase_sync


def _pasta_downloads():
    """Retorna o caminho da pasta Downloads no Windows e no Android."""
    if platform.system() == 'Android':
        return '/storage/emulated/0/Download'
    return os.path.join(os.path.expanduser('~'), 'Downloads')

_FONT_PATH = os.path.join(os.path.dirname(__file__), 'assets', 'fonts', 'ERASBD.TTF')
if not os.path.exists(_FONT_PATH):
    _FONT_PATH = 'C:/Windows/Fonts/ERASBD.TTF'  # fallback dev Windows
if os.path.exists(_FONT_PATH):
    LabelBase.register(name='ErasBoldITC', fn_regular=_FONT_PATH)

BASE_DIR     = os.path.dirname(__file__)
DATA_DIR     = os.path.join(BASE_DIR, 'data')
TREINOS_FILE       = os.path.join(DATA_DIR, 'treinos.json')
TREINOS_NOMES_FILE = os.path.join(DATA_DIR, 'treinos_nomes.json')
HISTORICO_FILE     = os.path.join(DATA_DIR, 'historico.json')
ATIVIDADE_FILE     = os.path.join(DATA_DIR, 'historico_atividade.json')
CLIENTE_FILE       = os.path.join(DATA_DIR, 'cliente.json')
SYNC_FILE          = os.path.join(DATA_DIR, 'ultima_sync.json')


class RonaldoMedeirosFisiologistaApp(MDApp):

    CLIENTE_FILE = CLIENTE_FILE   # acessível de tela_cadastro

    def build(self):
        self.title = 'Ronaldo Medeiros Fisiologista'
        self.theme_cls.primary_palette = 'Blue'
        self.theme_cls.theme_style = 'Dark'

        os.makedirs(DATA_DIR, exist_ok=True)
        self.pode_editar      = True
        self.treino_atual     = ''
        self.progresso_treino = {}
        self.cliente       = self._carregar(CLIENTE_FILE, None) or self._recuperar_cliente_downloads()
        self.treinos       = self._carregar(TREINOS_FILE,       {})
        self.treinos_nomes = self._carregar(TREINOS_NOMES_FILE, {})
        self.historico     = self._carregar(HISTORICO_FILE,     {})
        self.atividade     = self._carregar(ATIVIDADE_FILE,     [])

        from telas.tela_cadastro import TelaCadastro
        from telas.tela_home import TelaHome
        from telas.tela_treino import TelaTreino
        from telas.tela_historico import TelaHistorico
        from telas.tela_atividade import TelaAtividade
        from telas.tela_configuracoes import TelaConfiguracoes

        self.sm = ScreenManager(transition=SlideTransition())
        self.sm.add_widget(TelaCadastro(name='cadastro'))
        self.sm.add_widget(TelaHome(name='home'))
        self.sm.add_widget(TelaTreino(name='treino'))
        self.sm.add_widget(TelaHistorico(name='historico'))
        self.sm.add_widget(TelaAtividade(name='atividade'))
        self.sm.add_widget(TelaConfiguracoes(name='configuracoes'))

        # Primeira tela: cadastro se ainda não registrado, senão home
        self.sm.current = 'home' if self.cliente else 'cadastro'
        return self.sm

    def on_start(self):
        """Verifica se o treinador atualizou o plano de treino."""
        if self.cliente:
            threading.Thread(target=self._puxar_treinos_firebase, daemon=True).start()
            Clock.schedule_interval(self._verificar_sync_diario, 60)

    def on_resume(self):
        """Chamado quando o app volta ao primeiro plano no Android."""
        if self.cliente:
            threading.Thread(target=self._puxar_treinos_firebase, daemon=True).start()

    def _verificar_sync_diario(self, _dt):
        """Dispara sync automático às 5h da manhã, uma vez por dia."""
        agora = datetime.now()
        if agora.hour < 5:
            return
        hoje = agora.strftime('%d/%m/%Y')
        ultima = self._carregar(SYNC_FILE, '')
        if ultima == hoje:
            return
        with open(SYNC_FILE, 'w', encoding='utf-8') as f:
            json.dump(hoje, f)
        if self.cliente:
            threading.Thread(target=self._puxar_treinos_firebase, daemon=True).start()

    # ── dados ────────────────────────────────────────────────────────────────

    _CLIENTE_BACKUP = os.path.join(_pasta_downloads(), 'ronaldo_cliente_backup.json')

    def _recuperar_cliente_downloads(self):
        """Se cliente.json sumiu (reinstalação), tenta recuperar da Downloads."""
        dados = self._carregar(self._CLIENTE_BACKUP, None)
        if not (dados and dados.get('id') and dados.get('nome')):
            return None
        # Restaura cliente.json
        cliente = {'id': dados['id'], 'nome': dados['nome']}
        with open(CLIENTE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cliente, f, ensure_ascii=False, indent=2)
        # Restaura treinos, nomes e histórico se presentes no backup
        if dados.get('treinos'):
            with open(TREINOS_FILE, 'w', encoding='utf-8') as f:
                json.dump(dados['treinos'], f, ensure_ascii=False, indent=2)
        if dados.get('treinos_nomes'):
            with open(TREINOS_NOMES_FILE, 'w', encoding='utf-8') as f:
                json.dump(dados['treinos_nomes'], f, ensure_ascii=False, indent=2)
        if dados.get('historico'):
            with open(HISTORICO_FILE, 'w', encoding='utf-8') as f:
                json.dump(dados['historico'], f, ensure_ascii=False, indent=2)
        print('[Recuperação] Dados restaurados da Downloads.')
        return cliente

    def _carregar(self, path, default):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default

    def salvar(self):
        with open(TREINOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.treinos, f, ensure_ascii=False, indent=2)
        with open(HISTORICO_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.historico, f, ensure_ascii=False, indent=2)
        # Mantém backup na Downloads atualizado com os treinos mais recentes
        if self.cliente:
            try:
                backup = {**self.cliente, 'treinos': self.treinos, 'treinos_nomes': self.treinos_nomes, 'historico': self.historico}
                with open(self._CLIENTE_BACKUP, 'w', encoding='utf-8') as f:
                    json.dump(backup, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        # Sincroniza historico + atividade + obs com Firebase (treinos são do painel)
        if self.cliente:
            obs_map = {
                ex['id']: ex['obs']
                for exs in self.treinos.values()
                for ex in exs
                if ex.get('obs')
            }
            firebase_sync.salvar_dados(
                self.cliente['id'],
                self.historico,
                self.atividade,
                obs_map or None,
            )

    def recarregar_dados(self):
        """Relê os arquivos de dados do disco para a memória."""
        self.treinos       = self._carregar(TREINOS_FILE,       {'A': [], 'B': [], 'C': []})
        self.treinos_nomes = self._carregar(TREINOS_NOMES_FILE, {})
        self.historico     = self._carregar(HISTORICO_FILE,     {})
        self.atividade     = self._carregar(ATIVIDADE_FILE,     [])

    # ── Firebase: puxar mudanças do treinador ────────────────────────────────

    def _puxar_treinos_firebase(self):
        """Roda em thread. Se trainer_editou=True, aplica o treino novo."""
        dados = firebase_sync.buscar_cliente_completo(self.cliente['id'])
        if not dados:
            return
        Clock.schedule_once(
            lambda dt: setattr(MDApp.get_running_app(), 'pode_editar', dados.get('pode_editar', True)), 0
        )
        treino_atual = dados.get('treino_atual', '')
        Clock.schedule_once(
            lambda dt, v=treino_atual: setattr(MDApp.get_running_app(), 'treino_atual', v), 0
        )
        if dados.get('trainer_editou'):
            novos_treinos = dados['treinos']
            obs_cliente   = dados.get('obs_cliente', {})
            novos_nomes   = dados.get('treinos_nomes', {})
            Clock.schedule_once(
                lambda _, t=novos_treinos, o=obs_cliente, n=novos_nomes: self._aplicar_treinos_firebase(t, o, n), 0
            )

    def _aplicar_treinos_firebase(self, novos_treinos, obs_cliente=None, novos_nomes=None):
        """Chamado na thread principal. Substitui treinos e salva localmente."""
        if obs_cliente:
            for exs in novos_treinos.values():
                for ex in exs:
                    obs = obs_cliente.get(ex.get('id', ''))
                    if obs:
                        ex['obs'] = obs
        self.treinos = novos_treinos
        with open(TREINOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.treinos, f, ensure_ascii=False, indent=2)
        if novos_nomes is not None:
            self.treinos_nomes = novos_nomes
            with open(TREINOS_NOMES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.treinos_nomes, f, ensure_ascii=False, indent=2)
        firebase_sync.marcar_trainer_lido(self.cliente['id'])
        # Atualiza backup na Downloads com os treinos recebidos do treinador
        try:
            backup = {**self.cliente, 'treinos': self.treinos, 'treinos_nomes': self.treinos_nomes, 'historico': self.historico}
            with open(self._CLIENTE_BACKUP, 'w', encoding='utf-8') as f:
                json.dump(backup, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        # Atualiza a tela home se estiver visível
        try:
            self.sm.get_screen('home')._reconstruir_botoes()
        except Exception:
            pass
        print('[Firebase] Treinos atualizados pelo treinador.')

    # ── gerenciamento de treinos ──────────────────────────────────────────────

    LETRAS = ['A', 'B', 'C', 'D', 'E']

    def adicionar_exercicio(self, treino, nome, series, peso):
        ex_id = str(uuid.uuid4())
        ex = {'id': ex_id, 'nome': nome, 'series': series, 'peso': peso}
        self.treinos[treino].append(ex)
        self.historico[ex_id] = [
            {'data': datetime.now().strftime('%d/%m/%Y'), 'peso': peso}
        ]
        self.salvar()
        return ex

    def atualizar_exercicio(self, treino, ex_id, nome, series, peso):
        for ex in self.treinos[treino]:
            if ex['id'] == ex_id:
                if peso != ex['peso']:
                    if ex_id not in self.historico:
                        self.historico[ex_id] = []
                    self.historico[ex_id].append(
                        {'data': datetime.now().strftime('%d/%m/%Y'), 'peso': peso}
                    )
                ex['nome'] = nome
                ex['series'] = series
                ex['peso'] = peso
                self.salvar()
                break

    def remover_exercicio(self, treino, ex_id):
        self.treinos[treino] = [e for e in self.treinos[treino] if e['id'] != ex_id]
        self.salvar()

    def adicionar_treino(self):
        """Adiciona o próximo treino disponível (A→E). Máximo 5."""
        existentes = set(self.treinos.keys())
        for letra in self.LETRAS:
            if letra not in existentes:
                self.treinos[letra] = []
                self.salvar()
                return letra
        return None

    def remover_treino(self, letra):
        """Remove o treino e limpa o histórico de peso de seus exercícios."""
        exercicios = self.treinos.pop(letra, [])
        for ex in exercicios:
            self.historico.pop(ex['id'], None)
        self.salvar()

    # ── histórico de atividade ───────────────────────────────────────────────

    def registrar_set(self, treino, ex, serie_num, total_series):
        """Registra a conclusão de uma série. Marca concluido=True na última."""
        agora = datetime.now()
        entrada = {
            'data':         agora.strftime('%d/%m/%Y'),
            'hora':         agora.strftime('%H:%M:%S'),
            'treino':       treino,
            'ex_id':        ex['id'],
            'nome':         ex['nome'],
            'serie':        serie_num,
            'series_total': total_series,
            'peso':         ex['peso'],
            'concluido':    serie_num == total_series,
        }
        self.atividade.append(entrada)
        with open(ATIVIDADE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.atividade, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    RonaldoMedeirosFisiologistaApp().run()
