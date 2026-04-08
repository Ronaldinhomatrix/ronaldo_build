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


CARD_H        = dp(110)
COR_CONCLUIDO = get_color_from_hex('#388E3C')
COR_PENDENTE  = (0.35, 0.35, 0.35, 1)


class CardExercicio(MDCard):
    """Card de exercício com 3 linhas: nome+vídeo, séries, obs+feito."""

    def __init__(self, ex, tela, **kwargs):
        super().__init__(
            orientation='vertical',
            size_hint=(1, None),
            height=CARD_H,
            padding=[dp(12), dp(8), dp(12), dp(8)],
            spacing=dp(2),
            ripple_behavior=False,
            **kwargs,
        )
        self.ex = ex
        self.tela = tela
        app = MDApp.get_running_app()
        self._feito = app.progresso_treino.get('feitos', {}).get(ex.get('id', ''), False)
        self._build()

    def _build(self):
        tem_midia = bool(self.ex.get('midia_url', '').strip())

        # ── linha 1: nome + vídeo ─────────────────────────────────────────────
        linha1 = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(32),
        )
        linha1.add_widget(MDLabel(
            text=self.ex['nome'],
            font_style='Subtitle1',
            size_hint_x=1,
        ))
        if tem_midia:
            tipo = self.ex.get('midia_tipo', 'gif')
            icon = 'play-circle-outline' if tipo == 'video' else 'image-outline'
            linha1.add_widget(MDIconButton(
                icon=icon,
                theme_text_color='Custom',
                text_color=(0.6, 0.8, 1.0, 1),
                size_hint_x=None,
                on_release=lambda x: self.tela._ver_midia(self.ex),
            ))
        self.add_widget(linha1)

        # ── linha 2: séries e rep + peso ──────────────────────────────────────
        linha2 = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(22),
        )
        linha2.add_widget(MDLabel(
            text=f"Séries e Rep: {self.ex.get('series', '')}   •   Peso: {self.ex.get('peso', '')} kg",
            font_style='Caption',
            theme_text_color='Secondary',
        ))
        self.add_widget(linha2)

        # ── linha 3: observação + feito ───────────────────────────────────────
        linha3 = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(36),
            spacing=dp(8),
        )
        tem_obs = bool(self.ex.get('obs', '').strip())
        self._btn_obs = MDFlatButton(
            text='Observação',
            theme_text_color='Custom',
            text_color=(0.357, 0.612, 0.965, 1) if tem_obs else (0.6, 0.6, 0.6, 1),
            size_hint_x=None,
            on_release=lambda x: self.tela._editar_obs(self.ex, self),
        )
        linha3.add_widget(self._btn_obs)
        linha3.add_widget(MDBoxLayout(size_hint_x=1))  # espaçador
        self._btn_feito = MDRaisedButton(
            text='✓ Feito' if self._feito else 'Feito',
            size_hint=(None, None),
            size=(dp(80), dp(28)),
            font_size='11sp',
            rounded_button=True,
            md_bg_color=COR_CONCLUIDO if self._feito else COR_PENDENTE,
        )
        self._btn_feito.bind(on_release=self._toggle_feito)
        linha3.add_widget(self._btn_feito)
        self.add_widget(linha3)

    # ── botão Feito ───────────────────────────────────────────────────────────

    def _toggle_feito(self, *args):
        self._feito = not self._feito
        app = MDApp.get_running_app()
        app.progresso_treino.setdefault('feitos', {})[self.ex['id']] = self._feito
        if self._feito:
            self._btn_feito.text = '✓ Feito'
            self._btn_feito.md_bg_color = COR_CONCLUIDO
        else:
            self._btn_feito.text = 'Feito'
            self._btn_feito.md_bg_color = COR_PENDENTE
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
            rounded_button=True,
            disabled=True,
            md_bg_color=(0.25, 0.25, 0.25, 1),
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
        self._btn_concluir.text = 'Registrar treino completo'
        self._btn_concluir.md_bg_color = (0.25, 0.25, 0.25, 1)
        if app.progresso_treino.get('treino') != treino:
            app.progresso_treino = {'treino': treino, 'feitos': {}}
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
        todos = all(c._feito for c in self._cards)
        if todos:
            self._btn_concluir.text = 'Treino Registrado ✓'
            self._btn_concluir.md_bg_color = COR_CONCLUIDO
            self._btn_concluir.disabled = False
            # ── tudo automático ao completar ──────────────────────────────────
            app = MDApp.get_running_app()
            exercicios = [c.ex for c in self._cards]
            app.salvar(treino=self.treino_atual, exercicios_concluidos=exercicios)
            app.progresso_treino = {}
            if app.treino_atual and app.treino_atual == self.treino_atual and app.cliente:
                app.treino_atual = ''
                import firebase_sync
                firebase_sync.limpar_treino_atual(app.cliente['id'])
        else:
            self._btn_concluir.text = 'Registrar treino completo'
            self._btn_concluir.md_bg_color = (0.25, 0.25, 0.25, 1)
            self._btn_concluir.disabled = True

    def _concluir_treino(self):
        MDApp.get_running_app().sm.current = 'home'

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
