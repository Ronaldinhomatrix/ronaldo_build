import re

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.image import AsyncImage
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.videoplayer import VideoPlayer
from kivy.utils import get_color_from_hex
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDIconButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar


CARD_H        = dp(80)
COR_CONCLUIDO = get_color_from_hex('#388E3C')


def _parse_total_series(series_str):
    m = re.match(r'\s*(\d+)', str(series_str))
    return int(m.group(1)) if m else 1


class CardExercicio(MDCard):
    """Card de exercício com contador de séries, observações e mídia."""

    def __init__(self, ex, tela, **kwargs):
        super().__init__(
            orientation='horizontal',
            size_hint=(1, None),
            height=CARD_H,
            padding=[dp(12), dp(8), dp(8), dp(8)],
            spacing=dp(4),
            ripple_behavior=False,
            **kwargs,
        )
        self.ex = ex
        self.tela = tela
        self._total_series = _parse_total_series(ex.get('series', '1'))
        app = MDApp.get_running_app()
        saved = app.progresso_treino.get('series', {})
        self._series_feitas = min(saved.get(ex.get('id', ''), 0), self._total_series)
        self._build()
        if self._series_feitas >= self._total_series:
            Clock.schedule_once(lambda dt: setattr(self._btn_contador, 'md_bg_color', COR_CONCLUIDO), 0)

    def _build(self):
        # ── coluna de info ────────────────────────────────────────────────────
        info = MDBoxLayout(orientation='vertical', size_hint_x=1)

        info.add_widget(MDLabel(
            text=self.ex['nome'],
            font_style='Subtitle1',
            size_hint_y=None,
            height=dp(28),
        ))

        rodape = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(32),
            spacing=dp(4),
        )
        rodape.add_widget(MDLabel(
            text=f"{self.ex.get('series', '')}   •   {self.ex.get('peso', '')} kg",
            font_style='Caption',
            theme_text_color='Secondary',
            size_hint_x=1,
        ))

        texto_inicial = '✓' if self._series_feitas >= self._total_series else f'{self._series_feitas}/{self._total_series}'
        self._btn_contador = MDRaisedButton(
            text=texto_inicial,
            size_hint=(None, None),
            size=(dp(62), dp(28)),
            font_size='11sp',
        )
        self._btn_contador.bind(on_release=self._marcar_serie)
        rodape.add_widget(self._btn_contador)

        info.add_widget(rodape)
        self.add_widget(info)

        # ── ações ─────────────────────────────────────────────────────────────
        tem_midia = bool(self.ex.get('midia_url', '').strip())
        n_botoes  = 4 if tem_midia else 3
        acoes = MDBoxLayout(
            orientation='horizontal',
            size_hint_x=None,
            width=dp(44 * n_botoes),
        )

        acoes.add_widget(MDIconButton(
            icon='chart-line',
            on_release=lambda x: self.tela._ver_historico(self.ex),
        ))

        tem_obs = bool(self.ex.get('obs', '').strip())
        self._btn_obs = MDIconButton(
            icon='note-text' if tem_obs else 'note-text-outline',
            theme_text_color='Custom',
            text_color=(0.357, 0.612, 0.965, 1) if tem_obs else (0.6, 0.6, 0.6, 1),
            on_release=lambda x: self.tela._editar_obs(self.ex, self),
        )
        acoes.add_widget(self._btn_obs)

        acoes.add_widget(MDIconButton(
            icon='refresh',
            theme_text_color='Custom',
            text_color=(0.8, 0.4, 0.4, 1),
            on_release=lambda x: self._zerar_series(),
        ))

        if tem_midia:
            tipo = self.ex.get('midia_tipo', 'gif')
            icon = 'play-circle-outline' if tipo == 'video' else 'image-outline'
            acoes.add_widget(MDIconButton(
                icon=icon,
                theme_text_color='Custom',
                text_color=(0.6, 0.8, 1.0, 1),
                on_release=lambda x: self.tela._ver_midia(self.ex),
            ))

        self.add_widget(acoes)

    # ── contador de séries ────────────────────────────────────────────────────

    def _zerar_series(self):
        app = MDApp.get_running_app()
        app.progresso_treino.get('series', {}).pop(self.ex['id'], None)
        self._series_feitas = 0
        self._btn_contador.text = f'0/{self._total_series}'
        self._btn_contador.md_bg_color = self._btn_contador.theme_cls.primary_color
        self.tela._verificar_conclusao()

    def _marcar_serie(self, *args):
        if self._series_feitas >= self._total_series:
            return

        self._series_feitas += 1
        app = MDApp.get_running_app()
        app.progresso_treino.setdefault('series', {})[self.ex['id']] = self._series_feitas
        app.registrar_set(
            self.tela.treino_atual,
            self.ex,
            self._series_feitas,
            self._total_series,
        )

        if self._series_feitas < self._total_series:
            self._btn_contador.text = f'{self._series_feitas}/{self._total_series}'
        else:
            self._btn_contador.text = '✓'
            self._btn_contador.md_bg_color = COR_CONCLUIDO

        self.tela._verificar_conclusao()


class TelaTreino(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.treino_atual = None
        self.dialog       = None
        self._cards       = []
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation='vertical')

        self.toolbar = MDTopAppBar(
            title='Treino',
            left_action_items=[['arrow-left', lambda x: self._voltar()]],
        )
        root.add_widget(self.toolbar)

        # ── lista de exercícios ───────────────────────────────────────────────
        scroll = ScrollView()
        self.lista = MDBoxLayout(
            orientation='vertical',
            spacing=dp(8),
            padding=dp(12),
            size_hint_y=None,
        )
        self.lista.bind(minimum_height=self.lista.setter('height'))
        scroll.add_widget(self.lista)
        root.add_widget(scroll)

        # ── botão concluir treino ─────────────────────────────────────────────
        self._btn_concluir = MDRaisedButton(
            text='Registrar treino completo',
            size_hint=(1, None),
            height=dp(52),
            disabled=True,
            on_release=lambda x: self._concluir_treino(),
        )
        root.add_widget(self._btn_concluir)

        self.add_widget(root)

    # ── público ───────────────────────────────────────────────────────────────

    def carregar(self, treino):
        self.treino_atual = treino
        app  = MDApp.get_running_app()
        nome = app.treinos_nomes.get(treino, '')
        self.toolbar.title = f'Treino {treino} — {nome}' if nome else f'Treino {treino}'
        self._cards = []
        self._btn_concluir.disabled = True
        if app.progresso_treino.get('treino') != treino:
            app.progresso_treino = {'treino': treino, 'series': {}}
        self._renderizar()

    # ── renderização ──────────────────────────────────────────────────────────

    def _renderizar(self):
        self.lista.clear_widgets()
        self._cards = []
        app = MDApp.get_running_app()
        exercicios = app.treinos.get(self.treino_atual, [])

        if not exercicios:
            self.lista.add_widget(MDLabel(
                text='Nenhum exercício cadastrado.',
                halign='center',
                theme_text_color='Secondary',
                size_hint_y=None,
                height=dp(100),
            ))
            return

        for ex in exercicios:
            card = CardExercicio(ex=ex, tela=self)
            self._cards.append(card)
            self.lista.add_widget(card)

    # ── conclusão do treino ───────────────────────────────────────────────────

    def _verificar_conclusao(self):
        if not self._cards:
            return
        todos = all(c._series_feitas >= c._total_series for c in self._cards)
        self._btn_concluir.disabled = not todos

    def _concluir_treino(self):
        app = MDApp.get_running_app()
        app.salvar()
        app.progresso_treino = {}
        if app.treino_atual and app.treino_atual == self.treino_atual and app.cliente:
            app.treino_atual = ''
            import firebase_sync
            firebase_sync.limpar_treino_atual(app.cliente['id'])
        app.sm.current = 'home'

    # ── observações ───────────────────────────────────────────────────────────

    def _editar_obs(self, ex, card):
        campo = MDTextField(
            text=ex.get('obs', ''),
            hint_text='Observação sobre o exercício',
            mode='rectangle',
            multiline=True,
            size_hint_y=None,
            height=dp(80),
        )
        caixa = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(96),
            padding=[dp(16), dp(4), dp(16), dp(4)],
        )
        caixa.add_widget(campo)

        dlg = MDDialog(
            title=ex['nome'],
            type='custom',
            content_cls=caixa,
            buttons=[
                MDFlatButton(text='CANCELAR', on_release=lambda x: dlg.dismiss()),
                MDRaisedButton(text='SALVAR',  on_release=lambda x: self._salvar_obs(ex, card, campo.text, dlg)),
            ],
        )
        dlg.open()

    def _salvar_obs(self, ex, card, texto, dlg):
        ex['obs'] = texto.strip()
        app = MDApp.get_running_app()
        app.salvar()
        tem_obs = bool(ex['obs'])
        card._btn_obs.icon = 'note-text' if tem_obs else 'note-text-outline'
        card._btn_obs.text_color = (0.357, 0.612, 0.965, 1) if tem_obs else (0.6, 0.6, 0.6, 1)
        dlg.dismiss()
        if tem_obs and app.cliente:
            import firebase_sync
            firebase_sync.notificar_obs(app.cliente['nome'], ex['nome'], ex['obs'])

    # ── mídia ─────────────────────────────────────────────────────────────────

    def _ver_midia(self, ex):
        url  = ex.get('midia_url', '')
        tipo = ex.get('midia_tipo', 'gif')

        if tipo == 'video':
            player = VideoPlayer(
                source=url,
                state='play',
                allow_stretch=True,
            )
            popup = Popup(
                title=ex['nome'],
                content=player,
                size_hint=(1, 0.6),
            )
            popup.bind(on_dismiss=lambda p: setattr(player, 'state', 'stop'))
            popup.open()
            return

        # foto ou gif — exibe em dialog
        img = AsyncImage(
            source=url,
            size_hint_y=None,
            height=dp(280),
            allow_stretch=True,
            keep_ratio=True,
        )
        caixa = MDBoxLayout(size_hint_y=None, height=dp(280))
        caixa.add_widget(img)

        dlg = MDDialog(
            title=ex['nome'],
            type='custom',
            content_cls=caixa,
            buttons=[MDFlatButton(text='FECHAR', on_release=lambda x: dlg.dismiss())],
        )
        dlg.open()

    # ── histórico de peso ─────────────────────────────────────────────────────

    def _ver_historico(self, ex):
        app = MDApp.get_running_app()
        tela = app.sm.get_screen('historico')
        tela.carregar(ex)
        app.sm.current = 'historico'

    def _voltar(self):
        MDApp.get_running_app().sm.current = 'home'
