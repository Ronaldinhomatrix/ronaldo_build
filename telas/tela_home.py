import threading
from datetime import datetime

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.image import Image as KivyImage
from kivy.utils import get_color_from_hex
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDIconButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

COR_PROXIMO = get_color_from_hex('#2ECC71')  # Verde Esmeralda (Destaque do Dia)


class _BotaoTreino(MDCard):
    """Card-botão de treino com subtítulo de conclusão e destaque."""

    COR_PADRAO = get_color_from_hex('#2C2C2E')  # Cinza Grafite Suave

    def __init__(self, letra, nome, on_abrir, **kwargs):
        super().__init__(
            orientation='vertical',
            size_hint=(1, None),
            height=dp(72),
            padding=[dp(16), dp(8), dp(8), dp(8)],
            spacing=dp(2),
            ripple_behavior=True,
            radius=[dp(36)],
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
            text_color=(1, 1, 1, 1),  # Branco
            size_hint_x=1,
        ))

        self.add_widget(linha_titulo)

        # ── subtítulo de conclusão ────────────────────────────────────────────
        self._lbl_sub = MDLabel(
            text='',
            halign='center',
            font_style='Caption',
            theme_text_color='Custom',
            text_color=(0.8, 0.8, 0.8, 1),  # Cinza claro
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
        from kivy.uix.scrollview import ScrollView

        root = MDBoxLayout(orientation='vertical')

        # ── área rolável ──────────────────────────────────────────────────────
        scroll = ScrollView(size_hint=(1, 1))

        content = MDBoxLayout(
            orientation='vertical',
            padding=[dp(40), dp(24), dp(40), dp(24)],
            spacing=dp(16),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter('height'))

        # ── bloco título (foto + nome + fisiologista) ─────────────────────────
        titulo = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(12),
        )
        titulo.bind(minimum_height=titulo.setter('height'))

        tamanho_foto = Window.height * 0.26
        foto_row = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=tamanho_foto,
        )
        foto_row.add_widget(MDBoxLayout(size_hint_x=1))
        foto_row.add_widget(KivyImage(
            source='foto_perfil.jpg',
            size_hint=(None, None),
            size=(tamanho_foto, tamanho_foto),
            allow_stretch=True,
            keep_ratio=True,
        ))
        foto_row.add_widget(MDBoxLayout(size_hint_x=1))
        titulo.add_widget(foto_row)

        lbl_nome = MDLabel(
            text='Ronaldo Medeiros',
            halign='center',
            font_style='H3',
            size_hint_y=None,
            height=dp(64),
        )
        lbl_nome.bind(
            width=lambda inst, w: setattr(inst, 'text_size', (w, None)),
            texture_size=lambda inst, ts: setattr(inst, 'height', max(dp(64), ts[1])),
        )
        titulo.add_widget(lbl_nome)

        titulo.add_widget(MDBoxLayout(size_hint_y=None, height=dp(8)))

        titulo.add_widget(MDLabel(
            text='Fisiologista',
            halign='center',
            font_style='H6',
            theme_text_color='Custom',
            text_color=get_color_from_hex('#3498DB'),
            size_hint_y=None,
            height=dp(36),
        ))
        content.add_widget(titulo)

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

        # Container dinâmico dos botões
        self._container = MDBoxLayout(
            orientation='vertical',
            spacing=dp(12),
            size_hint_y=None,
        )
        self._container.bind(minimum_height=self._container.setter('height'))
        content.add_widget(self._container)

        scroll.add_widget(content)
        root.add_widget(scroll)

        # ── rodapé fixo (sempre visível, fora do scroll) ──────────────────────
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
            text='Sobre',
            size_hint_x=1,
            height=dp(44),
            on_release=lambda x: self._abrir_configuracoes(),
        ))
        root.add_widget(rodape)

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
