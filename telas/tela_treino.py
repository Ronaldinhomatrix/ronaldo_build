import os
import unicodedata

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


COR_CONCLUIDO = get_color_from_hex('#2ECC71')  # Verde Esmeralda
COR_ACCENT    = get_color_from_hex('#3498DB')  # Azul Peter River
COR_OBS       = get_color_from_hex('#F1C40F')  # Amarelo Girassol
COR_PENDENTE  = get_color_from_hex('#3E4A59')  # Azul Ardósia (mais visível que o cinza)


class CardExercicio(MDCard):
    """Card de exercício com borda lateral colorida e altura dinâmica."""

    @staticmethod
    def _caminho_video(nome):
        sem_acento = unicodedata.normalize('NFD', nome)
        sem_acento = ''.join(c for c in sem_acento if unicodedata.category(c) != 'Mn')
        arquivo = sem_acento.lower().replace(' ', '_') + '.mp4'
        from telas.tela_download import pasta_videos
        externo = os.path.join(pasta_videos(), arquivo)
        if os.path.exists(externo):
            return externo
        return os.path.join('assets', 'videos', arquivo)

    def __init__(self, ex, tela, **kwargs):
        super().__init__(
            orientation='horizontal',
            size_hint=(1, None),
            padding=0,
            spacing=0,
            ripple_behavior=True,
            md_bg_color=get_color_from_hex('#2C2C2E'),  # Fundo do card mais suave que o preto
            radius=[dp(12), dp(12), dp(12), dp(12)],   # Bordas arredondadas
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

        # ── borda lateral azul ────────────────────────────────────────────────
        borda = MDBoxLayout(
            size_hint=(None, 1),
            width=Window.width * 0.010,
            md_bg_color=COR_ACCENT,
        )
        self.add_widget(borda)

        # ── conteúdo vertical (altura calculada pelos filhos) ─────────────────
        _esp_linhas = Window.height * 0.008   # espaço entre linhas de info
        _esp_botoes = Window.height * 0.003   # espaço menor antes dos botões
        _pad_inf    = Window.height * 0.012   # padding inferior do card

        conteudo = MDBoxLayout(
            orientation='vertical',
            size_hint=(1, None),
            padding=[0, 0, 0, _pad_inf],
            spacing=0,
        )
        conteudo.bind(minimum_height=conteudo.setter('height'))
        conteudo.bind(height=self.setter('height'))

        # ── linha 1: nome + vídeo (header com fundo destacado) ───────────────
        _h1 = Window.height * 0.055   # altura linha 1 proporcional à tela

        _pad_h = Window.width  * 0.025   # padding horizontal padrão
        _pad_v = Window.height * 0.005   # padding vertical padrão

        linha1 = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=_h1,
            padding=[_pad_h, _pad_v, _pad_v, _pad_v],
            md_bg_color=get_color_from_hex('#5DADE2'), # Azul Celeste (Mais vivo e azulado)
        )
        lbl_nome = Label(
            text=self.ex['nome'],
            font_size='20sp',
            size_hint_x=1,
            color=(1, 1, 1, 1),
            halign='left',
            valign='middle',
        )
        lbl_nome.bind(size=lbl_nome.setter('text_size'))
        linha1.add_widget(lbl_nome)
        if self._tem_video:
            linha1.add_widget(MDIconButton(
                icon='play-circle-outline',
                theme_text_color='Custom',
                text_color=(0.6, 0.8, 1.0, 1),
                size_hint_x=None,
                pos_hint={'center_y': 0.5},
                on_release=lambda x: self.tela._ver_midia(self.ex),
            ))
        conteudo.add_widget(linha1)

        # ── Nova Linha: Observação do Treinador (Apenas se existir) ───────
        obs_trainer = self.ex.get('obs_trainer', '').strip()
        if obs_trainer:
            # Aumentamos o espaçamento antes da obs
            conteudo.add_widget(MDBoxLayout(size_hint_y=None, height=_esp_linhas * 1.5))
            
            _h_obs_t = Window.height * 0.04  # Altura levemente maior para a linha
            linha_obs_t = MDBoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=_h_obs_t,
                padding=[_pad_h, 0, _pad_h, 0],
            )
            linha_obs_t.add_widget(MDLabel(
                text=obs_trainer,  # Removido "Obs Ronaldo:"
                font_size='14sp',  # Aumentado levemente para 14sp
                italic=True,
                theme_text_color='Custom',
                text_color=get_color_from_hex('#3498DB'), # Azul de destaque
            ))
            conteudo.add_widget(linha_obs_t)
            
            # Aumentamos o espaçamento depois da obs
            conteudo.add_widget(MDBoxLayout(size_hint_y=None, height=_esp_linhas * 1.5))
        else:
            conteudo.add_widget(MDBoxLayout(size_hint_y=None, height=_esp_linhas))

        # ── linhas 2 e 3: séries/peso e repetições ───────────────────────────
        _h2        = Window.height * 0.038   # altura de cada linha de info

        series     = self.ex.get('series', '')
        repeticoes = self.ex.get('repeticoes', '')
        peso       = self.ex.get('peso', '')

        if repeticoes:
            # ── linha 2: Séries + Peso ────────────────────────────────────────
            linha2 = MDBoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=_h2,
                padding=[_pad_h, 0, _pad_h * 1.2, 0],
            )
            linha2.add_widget(MDLabel(
                text='Séries:',
                font_size='11sp',
                theme_text_color='Secondary',
                halign='center',
                size_hint_x=0.38,
            ))
            linha2.add_widget(MDLabel(
                text=series,
                font_size='16sp',
                theme_text_color='Primary',
                size_hint_x=0.09,
            ))
            linha2.add_widget(MDLabel(
                text=f'Peso:  {peso} kg',
                font_size='16sp',
                theme_text_color='Primary',
                halign='right',
                size_hint_x=0.53,
            ))
            conteudo.add_widget(linha2)
            conteudo.add_widget(MDBoxLayout(size_hint_y=None, height=_esp_linhas))

            # ── linha 3: Repetições ───────────────────────────────────────────
            linha3_rep = MDBoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=_h2,
                padding=[_pad_h, 0, _pad_h * 1.2, 0],
            )
            linha3_rep.add_widget(MDLabel(
                text='Repetições:',
                font_size='11sp',
                theme_text_color='Secondary',
                halign='center',
                size_hint_x=0.38,
            ))
            linha3_rep.add_widget(MDLabel(
                text=repeticoes,
                font_size='16sp',
                theme_text_color='Primary',
                size_hint_x=0.62,
            ))
            conteudo.add_widget(linha3_rep)
            conteudo.add_widget(MDBoxLayout(size_hint_y=None, height=_esp_botoes))

        else:
            # fallback para exercícios antigos sem campo repeticoes
            linha2 = MDBoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=_h2,
                padding=[_pad_h, 0, _pad_h * 1.2, 0],
            )
            linha2.add_widget(MDLabel(
                text=f"Séries e Rep: {series}   •   Peso: {peso} kg",
                font_size='16sp',
                theme_text_color='Secondary',
            ))
            conteudo.add_widget(linha2)
            conteudo.add_widget(MDBoxLayout(size_hint_y=None, height=_esp_botoes))

        # ── linha 3: observação + feito ───────────────────────────────────────
        _fs3   = '13sp'   # linha 3: botões, menor que linhas 1 e 2
        _h3    = Window.height * 0.081   # ≈ dp(36) × 1.6 em tela padrão
        _btn_w = Window.width  * 0.320   # ≈ dp(80) × 1.6 em tela padrão
        _btn_h = Window.height * 0.063   # ≈ dp(28) × 1.6 em tela padrão

        linha3 = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=_h3,
            spacing=0,
            padding=[_pad_v, 0, _pad_h, 0],
        )
        tem_obs = bool(self.ex.get('obs', '').strip())
        self._btn_obs = MDRaisedButton(
            text='Observação Registrada' if tem_obs else 'Adicionar Observação',
            size_hint=(None, None),
            size=(_btn_w, _btn_h),
            font_size=_fs3,
            rounded_button=True,
            md_bg_color=COR_CONCLUIDO if tem_obs else self._cor_pendente,
            on_release=lambda x: self.tela._editar_obs(self.ex, self),
        )
        linha3.add_widget(self._btn_obs)
        linha3.add_widget(MDBoxLayout(size_hint_x=1))
        self._btn_feito = MDRaisedButton(
            text='✓ Feito' if self._feito else 'Feito',
            size_hint=(None, None),
            size=(_btn_w, _btn_h),
            font_size=_fs3,
            rounded_button=True,
            md_bg_color=COR_CONCLUIDO if self._feito else self._cor_pendente,
        )
        self._btn_feito.bind(on_release=self._toggle_feito)
        linha3.add_widget(self._btn_feito)
        conteudo.add_widget(linha3)

        self.add_widget(conteudo)

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
            self._btn_feito.md_bg_color = self._cor_pendente
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
            md_bg_color=get_color_from_hex('#1A1A1A'), # Voltando ao Preto Carbono
            elevation=0,
            left_action_items=[['arrow-left', lambda x: self._voltar()]],
        )
        root.add_widget(self.toolbar)

        # ── lista de exercícios ───────────────────────────────────────────────
        _esp_cards  = Window.height * 0.030   # espaço entre cards
        _pad_lista  = Window.width  * 0.030   # padding lateral da lista

        scroll = ScrollView()
        self.lista = MDBoxLayout(
            orientation='vertical',
            spacing=_esp_cards,
            padding=_pad_lista,
            size_hint_y=None,
        )
        self.lista.bind(minimum_height=self.lista.setter('height'))
        scroll.add_widget(self.lista)
        root.add_widget(scroll)

        # ── botão concluir treino ─────────────────────────────────────────────
        self._btn_concluir = MDRaisedButton(
            text='Registrar treino completo',
            size_hint=(1, None),
            height=dp(56),
            rounded_button=True,
            md_bg_color=(0.2, 0.2, 0.25, 1),
            elevation=4,
            on_release=lambda x: self._confirmar_conclusao(),
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
        else:
            self._btn_concluir.text = 'Registrar treino completo'
            self._btn_concluir.md_bg_color = (0.25, 0.25, 0.25, 1)

    def _confirmar_conclusao(self):
        dlg = MDDialog(
            text='Registrar treino completo?',
            buttons=[
                MDRaisedButton(
                    text='Sim',
                    md_bg_color=COR_CONCLUIDO,
                    on_release=lambda x: self._executar_conclusao(dlg),
                ),
                MDRaisedButton(
                    text='Não',
                    md_bg_color=(0.75, 0.1, 0.1, 1),
                    on_release=lambda x: dlg.dismiss(),
                ),
            ],
        )
        dlg.open()

    def _executar_conclusao(self, dlg):
        dlg.dismiss()
        app = MDApp.get_running_app()
        
        # 1. Marcar todos como feitos e LIMPAR observações
        for card in self._cards:
            # Marca como feito visualmente
            if not card._feito:
                card._feito = True
                card._btn_feito.text = '✓ Feito'
                card._btn_feito.md_bg_color = COR_CONCLUIDO
            
            # Limpa a observação do exercício no dicionário e visualmente no card
            card.ex['obs'] = ""
            card._btn_obs.text = 'Adicionar Observação'
            card._btn_obs.md_bg_color = card._cor_pendente

        # 2. Salva o treino concluído (isso envia o histórico e as observações limpas ao Firebase)
        exercicios = [c.ex for c in self._cards]
        app.salvar(treino=self.treino_atual, exercicios_concluidos=exercicios)
        
        # 3. Limpa progresso temporário e volta pra home
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
        
        dlg.dismiss()

        if tem_obs and app.cliente:
            # Estado: Enviando... (Amarelo Girassol)
            card._btn_obs.text = 'Enviando...'
            card._btn_obs.md_bg_color = COR_OBS
            
            def on_confirmado():
                # Estado: Registrado (Verde Esmeralda)
                card._btn_obs.text = 'Observação Registrada'
                card._btn_obs.md_bg_color = COR_CONCLUIDO

            def on_erro(msg):
                card._btn_obs.text = 'Erro (Tentar de novo)'
                card._btn_obs.md_bg_color = (0.8, 0.1, 0.1, 1) # Vermelho
                print(f"Erro ao enviar observação: {msg}")

            import firebase_sync
            firebase_sync.notificar_obs(
                app.cliente['nome'], 
                ex['nome'], 
                ex['obs'], 
                on_success=on_confirmado,
                on_error=on_erro
            )
        else:
            # Se limpou a observação
            card._btn_obs.text = 'Adicionar Observação'
            card._btn_obs.md_bg_color = card._cor_pendente

    # ── mídia ─────────────────────────────────────────────────────────────────

    def _ver_midia(self, ex):
        try:
            from kivy.uix.videoplayer import VideoPlayer
            caminho = CardExercicio._caminho_video(ex.get('nome', ''))
            player = VideoPlayer(
                source=caminho,
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
        except Exception as e:
            print(f"Erro ao carregar vídeo: {e}")
            self.dialog_erro = MDDialog(
                title="Vídeo Indisponível",
                text="Não foi possível reproduzir o vídeo neste dispositivo.\nNo Windows, verifique se o 'ffpyplayer' está instalado.",
                buttons=[MDRaisedButton(text="FECHAR", on_release=lambda x: self.dialog_erro.dismiss())]
            )
            self.dialog_erro.open()

    # ── histórico de peso ─────────────────────────────────────────────────────

    def _ver_historico(self, ex):
        app = MDApp.get_running_app()
        tela = app.sm.get_screen('historico')
        tela.carregar(ex)
        app.sm.current = 'historico'

    def _voltar(self):
        MDApp.get_running_app().sm.current = 'home'
