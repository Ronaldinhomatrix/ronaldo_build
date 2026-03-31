import threading
from datetime import datetime

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDIconButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

COR_PROXIMO = (0.05, 0.30, 0.12, 1.0)


class _BotaoTreino(MDCard):
    """Card-botão de treino com subtítulo de conclusão e destaque."""

    COR_PADRAO = (0.75, 0.75, 0.75, 1)

    def __init__(self, letra, nome, on_abrir, **kwargs):
        super().__init__(
            orientation='vertical',
            size_hint=(1, None),
            height=dp(72),
            padding=[dp(16), dp(8), dp(8), dp(8)],
            spacing=dp(2),
            ripple_behavior=True,
            radius=[dp(20)],
            md_bg_color=self.COR_PADRAO,
            **kwargs,
        )
        self._cor_padrao = self.COR_PADRAO
        self._verde_pendente = False

        # ── linha do título ───────────────────────────────────────────────────
        linha_titulo = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(36),
        )
        titulo_texto = f'Treino  {letra}  —  {nome}' if nome else f'Treino  {letra}'
        linha_titulo.add_widget(MDLabel(
            text=titulo_texto,
            halign='center',
            font_style='H6',
            theme_text_color='Custom',
            text_color=(0.1, 0.1, 0.1, 1),
            size_hint_x=1,
        ))

        self.add_widget(linha_titulo)

        # ── subtítulo de conclusão ────────────────────────────────────────────
        self._lbl_sub = MDLabel(
            text='',
            halign='center',
            font_style='Caption',
            theme_text_color='Custom',
            text_color=(0.3, 0.3, 0.3, 1),
            size_hint_y=None,
            height=dp(0),
            opacity=0,
        )
        self.add_widget(self._lbl_sub)

        self.bind(on_release=lambda *_: on_abrir(letra))

    # ── cor ───────────────────────────────────────────────────────────────────

    def destacar(self, verde):
        self.md_bg_color = COR_PROXIMO if verde else self._cor_padrao

    # ── subtítulo ─────────────────────────────────────────────────────────────

    def atualizar_status(self, data_conclusao, hora_conclusao, hoje):
        if data_conclusao:
            prefixo = 'hoje' if data_conclusao == hoje else data_conclusao[:5]
            self._lbl_sub.text = f'Concluído {prefixo} às {hora_conclusao}'
            self._lbl_sub.height = dp(20)
            self._lbl_sub.opacity = 1
            self.height = dp(80)
        else:
            self._lbl_sub.text = ''
            self._lbl_sub.height = dp(0)
            self._lbl_sub.opacity = 0
            self.height = dp(72)


class TelaHome(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dialog_remover = None
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation='vertical')

        # ── conteúdo ─────────────────────────────────────────────────────────
        content = MDBoxLayout(
            orientation='vertical',
            padding=dp(40),
            spacing=dp(16),
        )

        content.add_widget(MDBoxLayout(size_hint_y=0.2))

        titulo = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(88),
            spacing=0,
        )
        # font_size dinâmico: 7% da largura da tela, entre 22sp e 38sp
        _fs = max(22, min(38, int(Window.width * 0.07)))
        titulo.add_widget(MDLabel(
            text='Ronaldo Medeiros',
            halign='center',
            font_size=f'{_fs}sp',
            size_hint_y=None,
            height=dp(52),
        ))
        titulo.add_widget(MDLabel(
            text='Fisiologista',
            halign='center',
            font_style='H6',
            theme_text_color='Custom',
            text_color=(0.357, 0.612, 0.965, 1),
            size_hint_y=None,
            height=dp(36),
        ))
        content.add_widget(titulo)

        content.add_widget(MDBoxLayout(size_hint_y=0.03))

        self._lbl_saudacao = MDLabel(
            text='',
            halign='center',
            font_style='H6',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(36),
        )
        content.add_widget(self._lbl_saudacao)

        content.add_widget(MDLabel(
            text='Qual o nosso treino de hoje?',
            halign='center',
            font_style='Subtitle1',
            theme_text_color='Custom',
            text_color=(0.702, 0.702, 0.702, 1),
            size_hint_y=None,
            height=dp(36),
        ))

        content.add_widget(MDBoxLayout(size_hint_y=0.05))

        # Container dinâmico dos botões
        self._container = MDBoxLayout(
            orientation='vertical',
            spacing=dp(12),
            size_hint_y=None,
        )
        self._container.bind(minimum_height=self._container.setter('height'))
        content.add_widget(self._container)

        content.add_widget(MDBoxLayout(size_hint_y=0.08))

        self._lbl_sync = MDLabel(
            text='',
            halign='center',
            font_style='Caption',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(20),
        )
        content.add_widget(self._lbl_sync)

        rodape = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(44),
            spacing=dp(8),
        )
        rodape.add_widget(MDFlatButton(
            text='Histórico',
            size_hint_x=1,
            height=dp(44),
            on_release=lambda x: self._abrir_historico_atividade(),
        ))
        rodape.add_widget(MDFlatButton(
            text='Sincronizar',
            size_hint_x=1,
            height=dp(44),
            on_release=lambda x: self._sincronizar(),
        ))
        rodape.add_widget(MDFlatButton(
            text='Configurações',
            size_hint_x=1,
            height=dp(44),
            on_release=lambda x: self._abrir_configuracoes(),
        ))
        content.add_widget(rodape)

        content.add_widget(MDBoxLayout(size_hint_y=1))


        root.add_widget(content)

        self.add_widget(root)

    def on_enter(self, *args):
        self._atualizar_saudacao()
        self._reconstruir_botoes()

    def _atualizar_saudacao(self):
        app = MDApp.get_running_app()
        if not app.cliente:
            return
        primeiro_nome = app.cliente['nome'].split()[0]
        hora = datetime.now().hour
        if hora < 12:
            periodo = 'Bom dia'
        elif hora < 18:
            periodo = 'Boa tarde'
        else:
            periodo = 'Boa noite'
        self._lbl_saudacao.text = f'{periodo}, {primeiro_nome}!'

    # ── montagem dinâmica ─────────────────────────────────────────────────────

    def _reconstruir_botoes(self):
        app = MDApp.get_running_app()
        hoje = datetime.now().strftime('%d/%m/%Y')
        letras = sorted(app.treinos.keys())
        proximo = _proximo_treino(app)

        self._container.clear_widgets()

        for letra in letras:
            nome = app.treinos_nomes.get(letra, '')
            btn  = _BotaoTreino(letra=letra, nome=nome, on_abrir=self._ir)
            data, hora = _ultima_conclusao_treino(app, letra, hoje)
            btn.atualizar_status(data, hora, hoje)
            btn.destacar(letra == proximo)
            self._container.add_widget(btn)

    # ── ações ─────────────────────────────────────────────────────────────────

    def _ir(self, treino):
        app = MDApp.get_running_app()
        tela = app.sm.get_screen('treino')
        tela.carregar(treino)
        app.sm.current = 'treino'

    def _sincronizar(self):
        app = MDApp.get_running_app()
        if not app.cliente:
            return
        self._lbl_sync.text = 'Sincronizando...'
        def _run():
            import firebase_sync
            dados = firebase_sync.buscar_cliente_completo(app.cliente['id'])
            def _aplicar(dt):
                if dados is None:
                    self._lbl_sync.text = 'Erro ao conectar com o servidor.'
                    return
                if dados.get('trainer_editou'):
                    app._aplicar_treinos_firebase(dados['treinos'])
                    self._lbl_sync.text = 'Treinos atualizados!'
                    self._reconstruir_botoes()
                else:
                    self._lbl_sync.text = 'Treinos já estão atualizados.'
                Clock.schedule_once(lambda dt2: setattr(self._lbl_sync, 'text', ''), 4)
            Clock.schedule_once(_aplicar, 0)
        threading.Thread(target=_run, daemon=True).start()

    def _abrir_historico_atividade(self):
        MDApp.get_running_app().sm.current = 'atividade'

    def _abrir_configuracoes(self):
        MDApp.get_running_app().sm.current = 'configuracoes'


# ── funções auxiliares ────────────────────────────────────────────────────────

def _ultima_conclusao_treino(app, treino, hoje):
    """Retorna (data, hora) da última conclusão completa do treino, ou ('', '')."""
    exercicios = app.treinos.get(treino, [])
    if not exercicios:
        return '', ''
    ultima_dt = None
    ultima_data = ''
    ultima_hora = ''
    for reg in app.atividade:
        if reg.get('treino') == treino and reg.get('concluido'):
            try:
                dt = datetime.strptime(
                    f"{reg['data']} {reg['hora']}", '%d/%m/%Y %H:%M:%S'
                )
                if ultima_dt is None or dt > ultima_dt:
                    ultima_dt = dt
                    ultima_data = reg['data']
                    ultima_hora = reg['hora'][:5]
            except (ValueError, KeyError):
                pass
    # Só conta se todos os exercícios foram concluídos nessa data
    if not ultima_data:
        return '', ''
    for ex in exercicios:
        concluido = any(
            r.get('ex_id') == ex['id']
            and r.get('data') == ultima_data
            and r.get('concluido')
            for r in app.atividade
        )
        if not concluido:
            return '', ''
    return ultima_data, ultima_hora


def _proximo_treino(app):
    letras = sorted(app.treinos.keys())
    if not letras:
        return None
    # Treinador definiu manualmente
    if app.treino_atual and app.treino_atual in app.treinos:
        return app.treino_atual
    # Calcula pelo histórico
    ultima = {}
    for letra in letras:
        dt_max = None
        for reg in app.atividade:
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
        return None
    return min(letras, key=lambda l: ultima[l] or datetime.min)
