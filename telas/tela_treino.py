import os
import unicodedata
import platform

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
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

COR_CONCLUIDO = get_color_from_hex('#2ECC71')
COR_ACCENT    = get_color_from_hex('#3498DB')
COR_OBS       = get_color_from_hex('#F1C40F')
COR_PENDENTE  = get_color_from_hex('#3D3D3D')

class CardExercicio(MDCard):
    @staticmethod
    def _caminho_video(nome):
        # Normalização rigorosa para encontrar o arquivo
        sem_acento = unicodedata.normalize('NFD', nome)
        sem_acento = ''.join(c for c in sem_acento if unicodedata.category(c) != 'Mn')
        arquivo = sem_acento.lower().strip().replace(' ', '_') + '.mp4'
        
        from telas.tela_download import pasta_videos
        externo = os.path.join(pasta_videos(), arquivo)
        
        if os.path.exists(externo):
            return externo
            
        # Fallback para assets - no Android, assets devem ser acessados sem o prefixo 'assets/' 
        # se estiverem na raiz do source.dir, mas como estão em assets/videos/
        path_assets = os.path.join('assets', 'videos', arquivo)
        return path_assets

    def __init__(self, ex, tela, **kwargs):
        super().__init__(
            orientation='horizontal',
            size_hint=(1, None),
            padding=0,
            spacing=0,
            ripple_behavior=True,
            md_bg_color=get_color_from_hex('#2C2C2E'),
            radius=[dp(12), dp(12), dp(12), dp(12)],
            elevation=2,
            **kwargs,
        )
        self.ex = ex
        self.tela = tela
        app = MDApp.get_running_app()
        self._feito = app.progresso_treino.get('feitos', {}).get(ex.get('id', ''), False)
        self._cor_pendente = COR_PENDENTE
        self._tem_video = os.path.exists(self._caminho_video(ex.get('nome', '')))
        self._build()

    def _build(self):
        borda = MDBoxLayout(size_hint=(None, 1), width=Window.width * 0.010, md_bg_color=COR_ACCENT)
        self.add_widget(borda)

        _esp_linhas = Window.height * 0.008
        _esp_botoes = Window.height * 0.003
        _pad_inf    = Window.height * 0.012

        conteudo = MDBoxLayout(orientation='vertical', size_hint=(1, None), padding=[0, 0, 0, _pad_inf], spacing=0)
        conteudo.bind(minimum_height=conteudo.setter('height'))
        conteudo.bind(height=self.setter('height'))

        linha1 = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=Window.height * 0.055, padding=[Window.width * 0.025, Window.height * 0.005], md_bg_color=get_color_from_hex('#5DADE2'))
        lbl_nome = Label(text=self.ex['nome'], font_size='20sp', size_hint_x=1, color=(1, 1, 1, 1), halign='left', valign='middle')
        lbl_nome.bind(size=lbl_nome.setter('text_size'))
        linha1.add_widget(lbl_nome)
        if self._tem_video:
            linha1.add_widget(MDIconButton(icon='play-circle-outline', theme_text_color='Custom', text_color=(0.6, 0.8, 1.0, 1), size_hint_x=None, pos_hint={'center_y': 0.5}, on_release=lambda x: self.tela._ver_midia(self.ex)))
        conteudo.add_widget(linha1)

        obs_trainer = self.ex.get('obs_trainer', '').strip()
        if obs_trainer:
            conteudo.add_widget(MDBoxLayout(size_hint_y=None, height=_esp_linhas * 1.5))
            linha_obs_t = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=Window.height * 0.04, padding=[Window.width * 0.025, 0])
            linha_obs_t.add_widget(MDLabel(text=obs_trainer, font_size='14sp', italic=True, theme_text_color='Custom', text_color=get_color_from_hex('#3498DB')))
            conteudo.add_widget(linha_obs_t)
            conteudo.add_widget(MDBoxLayout(size_hint_y=None, height=_esp_linhas * 1.5))
        else:
            conteudo.add_widget(MDBoxLayout(size_hint_y=None, height=_esp_linhas))

        _h2 = Window.height * 0.038
        series = self.ex.get('series', '')
        repeticoes = self.ex.get('repeticoes', '')
        peso = self.ex.get('peso', '')

        linha2 = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=_h2, padding=[Window.width * 0.025, 0, Window.width * 0.025 * 1.2, 0])
        linha2.add_widget(MDLabel(text='Séries:', font_size='11sp', theme_text_color='Secondary', halign='center', size_hint_x=0.38))
        linha2.add_widget(MDLabel(text=series, font_size='16sp', theme_text_color='Primary', size_hint_x=0.09))
        linha2.add_widget(MDLabel(text=f'Peso:  {peso} kg', font_size='16sp', theme_text_color='Primary', halign='right', size_hint_x=0.53))
        conteudo.add_widget(linha2)
        conteudo.add_widget(MDBoxLayout(size_hint_y=None, height=_esp_linhas))

        if repeticoes:
            linha3_rep = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=_h2, padding=[Window.width * 0.025, 0, Window.width * 0.025 * 1.2, 0])
            linha3_rep.add_widget(MDLabel(text='Repetições:', font_size='11sp', theme_text_color='Secondary', halign='center', size_hint_x=0.38))
            linha3_rep.add_widget(MDLabel(text=repeticoes, font_size='16sp', theme_text_color='Primary', size_hint_x=0.62))
            conteudo.add_widget(linha3_rep)
            conteudo.add_widget(MDBoxLayout(size_hint_y=None, height=_esp_botoes))

        linha3 = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=Window.height * 0.081, spacing=0, padding=[Window.height * 0.005, 0, Window.width * 0.025, 0])
        tem_obs = bool(self.ex.get('obs', '').strip())
        self._btn_obs = MDRaisedButton(text='Observação Registrada' if tem_obs else 'Adicionar Observação', size_hint=(None, None), size=(Window.width * 0.320, Window.height * 0.063), font_size='13sp', rounded_button=True, md_bg_color=COR_CONCLUIDO if tem_obs else self._cor_pendente, on_release=lambda x: self.tela._editar_obs(self.ex, self))
        linha3.add_widget(self._btn_obs)
        linha3.add_widget(MDBoxLayout(size_hint_x=1))
        self._btn_feito = MDRaisedButton(text='✓ Feito' if self._feito else 'Feito', size_hint=(None, None), size=(Window.width * 0.320, Window.height * 0.063), font_size='13sp', rounded_button=True, md_bg_color=COR_CONCLUIDO if self._feito else self._cor_pendente)
        self._btn_feito.bind(on_release=self._toggle_feito)
        linha3.add_widget(self._btn_feito)
        conteudo.add_widget(linha3)
        self.add_widget(conteudo)

    def _toggle_feito(self, *args):
        self._feito = not self._feito
        app = MDApp.get_running_app()
        app.progresso_treino.setdefault('feitos', {})[self.ex['id']] = self._feito
        self._btn_feito.text = '✓ Feito' if self._feito else 'Feito'
        self._btn_feito.md_bg_color = COR_CONCLUIDO if self._feito else self._cor_pendente
        self.tela._verificar_conclusao()

class TelaTreino(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cards = []
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation='vertical')
        self.toolbar = MDTopAppBar(title='Treino', md_bg_color=get_color_from_hex('#1A1A1A'), elevation=0, left_action_items=[['arrow-left', lambda x: self._voltar()]])
        root.add_widget(self.toolbar)
        scroll = ScrollView()
        self.lista = MDBoxLayout(orientation='vertical', spacing=Window.height * 0.030, padding=Window.width * 0.030, size_hint_y=None)
        self.lista.bind(minimum_height=self.lista.setter('height'))
        scroll.add_widget(self.lista)
        root.add_widget(scroll)
        self._btn_concluir = MDRaisedButton(text='Registrar treino completo', size_hint=(1, None), height=dp(56), rounded_button=True, md_bg_color=(0.2, 0.2, 0.25, 1), on_release=lambda x: self._confirmar_conclusao())
        root.add_widget(self._btn_concluir)
        self.add_widget(root)

    def carregar(self, treino):
        self.treino_atual = treino
        app = MDApp.get_running_app()
        nome = app.treinos_nomes.get(treino, '')
        self.toolbar.title = f'Treino {treino} — {nome}' if nome else f'Treino {treino}'
        self.lista.clear_widgets()
        self._cards = []
        if app.progresso_treino.get('treino') != treino: app.progresso_treino = {'treino': treino, 'feitos': {}}
        for ex in app.treinos.get(treino, []):
            card = CardExercicio(ex=ex, tela=self)
            self._cards.append(card)
            self.lista.add_widget(card)
        self._verificar_conclusao()

    def _verificar_conclusao(self):
        if not self._cards: return
        todos = all(c._feito for c in self._cards)
        self._btn_concluir.text = 'Treino Registrado ✓' if todos else 'Registrar treino completo'
        self._btn_concluir.md_bg_color = COR_CONCLUIDO if todos else (0.2, 0.2, 0.25, 1)

    def _confirmar_conclusao(self):
        dlg = MDDialog(text='Registrar treino completo?', buttons=[
            MDRaisedButton(text='Sim', md_bg_color=COR_CONCLUIDO, on_release=lambda x: self._executar_conclusao(dlg)),
            MDRaisedButton(text='Não', md_bg_color=(0.75, 0.1, 0.1, 1), on_release=lambda x: dlg.dismiss()),
        ])
        dlg.open()

    def _executar_conclusao(self, dlg):
        dlg.dismiss()
        app = MDApp.get_running_app()
        for card in self._cards: card.ex['obs'] = ""
        app.salvar(treino=self.treino_atual, exercicios_concluidos=[c.ex for c in self._cards])
        app.progresso_treino = {}
        app.sm.current = 'home'

    def _editar_obs(self, ex, card):
        campo = MDTextField(text=ex.get('obs', ''), hint_text='Observação sobre o exercício', mode='rectangle', multiline=True, size_hint_y=None, height=dp(80))
        caixa = MDBoxLayout(orientation='vertical', size_hint_y=None, height=dp(96), padding=[dp(16), dp(4), dp(16), dp(4)])
        caixa.add_widget(campo)
        dlg = MDDialog(title=ex['nome'], type='custom', content_cls=caixa, buttons=[
            MDFlatButton(text='CANCELAR', on_release=lambda x: dlg.dismiss()),
            MDRaisedButton(text='SALVAR', on_release=lambda x: self._salvar_obs(ex, card, campo.text, dlg)),
        ])
        dlg.open()

    def _salvar_obs(self, ex, card, texto, dlg):
        ex['obs'] = texto.strip()
        app = MDApp.get_running_app()
        app.salvar()
        tem_obs = bool(ex['obs'])
        dlg.dismiss()
        if tem_obs and app.cliente:
            card._btn_obs.text = 'Enviando...'
            card._btn_obs.md_bg_color = COR_OBS
            import firebase_sync
            firebase_sync.notificar_obs(app.cliente['nome'], ex['nome'], ex['obs'], on_success=lambda: self._on_obs_sucesso(card), on_error=lambda m: self._on_obs_erro(card, m))
        else:
            card._btn_obs.text = 'Adicionar Observação'
            card._btn_obs.md_bg_color = card._cor_pendente

    def _on_obs_sucesso(self, card):
        card._btn_obs.text = 'Observação Registrada'
        card._btn_obs.md_bg_color = COR_CONCLUIDO

    def _on_obs_erro(self, card, msg):
        card._btn_obs.text = 'Erro (Tentar de novo)'
        card._btn_obs.md_bg_color = (0.8, 0.1, 0.1, 1)

    def _ver_midia(self, ex):
        try:
            from kivy.uix.video import Video
            caminho = CardExercicio._caminho_video(ex.get('nome', ''))
            
            # No Android, não podemos usar os.path.exists para arquivos dentro do APK (assets)
            # Então só validamos se for um caminho externo (fora do APK)
            if '/' in caminho and not caminho.startswith('assets') and not os.path.exists(caminho):
                MDDialog(text=f"Vídeo não encontrado:\n{os.path.basename(caminho)}").open()
                return

            # Criamos o widget de vídeo. 
            # Importante: No Android, o H.265 pode falhar se o provider não estiver pronto.
            video = Video(
                source=caminho,
                state='stop', # Começa parado para carregar com calma
                options={'eos': 'loop'},
                allow_stretch=True
            )
            
            popup = Popup(
                title=ex['nome'],
                content=video,
                size_hint=(0.9, 0.8),
                background_color=(0, 0, 0, 0.9)
            )
            
            # Agenda o início do vídeo para um frame depois da abertura do popup
            # Isso evita crash de renderização simultânea
            def start_video(*args):
                video.state = 'play'
            
            popup.bind(on_open=start_video)
            popup.bind(on_dismiss=lambda p: setattr(video, 'state', 'stop'))
            popup.open()
            
        except Exception as e:
            MDDialog(text=f"Erro ao carregar vídeo: {e}").open()

    def _voltar(self):
        MDApp.get_running_app().sm.current = 'home'
