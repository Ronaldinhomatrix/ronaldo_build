import random
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
from kivymd.uix.fitimage import FitImage
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

COR_PROXIMO = get_color_from_hex('#2ECC71')  # Verde Esmeralda (Destaque do Dia)

FRASES_MOTIVACIONAIS = [
    "O exercício é o único remédio que não tem efeitos colaterais negativos.",
    "Seu corpo é uma máquina biológica feita para o movimento. Mantenha-a ativa.",
    "A fisiologia não mente: o esforço de hoje é a saúde de amanhã.",
    "Treinar não é apenas estética, é otimização metabólica.",
    "O movimento inteligente previne o que a medicina nem sempre cura.",
    "O movimento é a cura.",
    "Consistência vence a intensidade em qualquer plano.",
    "Seu melhor treino é aquele que você não desistiu de fazer.",
    "Pequenos progressos diários geram resultados extraordinários.",
    "Não pare quando estiver cansado, pare quando estiver feito.",
    "Respeite seus limites, mas nunca pare de desafiá-los.",
    "Cada repetição te deixa mais longe da sua versão antiga.",
    "Seu corpo agradece cada gota de suor dedicada à saúde.",
    "A dor do treino é passageira, mas a saúde é para sempre.",
    "A disciplina é a ponte entre seus objetivos e suas conquistas."
]


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

    def set_status(self, texto):
        self._lbl_status.text = texto

    def _build(self):
        from kivy.uix.scrollview import ScrollView

        root = MDBoxLayout(orientation='vertical')
        
        # Pequeno status bar no topo para debug
        self._lbl_status = MDLabel(
            text='v3.16',
            halign='right',
            font_style='Caption',
            theme_text_color='Hint',
            size_hint_y=None,
            height=dp(20),
            padding=[0, 0, dp(10), 0]
        )
        root.add_widget(self._lbl_status)

        # ── área rolável ──────────────────────────────────────────────────────
        self.scroll = ScrollView(size_hint=(1, 1))

        content = MDBoxLayout(
            orientation='vertical',
            padding=[dp(40), dp(24), dp(40), dp(24)],
            spacing=dp(16),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter('height'))

        # ── bloco título (foto + nome + fisiologista) ─────────────────────────
        header = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=[0, dp(30), 0, dp(20)], # Aumentado padding para dar mais respiro
            spacing=dp(15),                 # Espaçamento entre foto e nome aumentado
        )
        header.bind(minimum_height=header.setter('height'))

        # Foto com borda e destaque (Tamanho fixo inicial para evitar crash)
        tamanho_foto = dp(160)
        
        foto_card = MDCard(
            size_hint=(None, None),
            size=(tamanho_foto, tamanho_foto),
            radius=[tamanho_foto/2, tamanho_foto/2, tamanho_foto/2, tamanho_foto/2],
            md_bg_color=(0, 0, 0, 0),
            line_color=get_color_from_hex('#5DADE2'),
            line_width=dp(1.5),
            elevation=0,
            pos_hint={'center_x': 0.5},
        )
        
        # FitImage é ideal para fotos circulares sem vazamentos
        sua_foto = FitImage(
            source='foto_perfil.jpg',
            size_hint=(1, 1),
            radius=[tamanho_foto/2, tamanho_foto/2, tamanho_foto/2, tamanho_foto/2],
        )
        foto_card.add_widget(sua_foto)
        header.add_widget(foto_card)

        # Nome com altura dinâmica para evitar sobreposição se quebrar linha
        lbl_nome = MDLabel(
            text='Ronaldo Medeiros',
            halign='center',
            font_style='H3', # Aumentado de H4 para H3
            bold=True,
            size_hint_y=None,
        )
        # Ajuste dinâmico de altura para o nome
        lbl_nome.bind(
            width=lambda inst, w: setattr(inst, 'text_size', (w, None)),
            texture_size=lambda inst, ts: setattr(inst, 'height', max(dp(64), ts[1])),
        )
        header.add_widget(lbl_nome)

        header.add_widget(MDLabel(
            text='Fisiologista',
            halign='center',
            font_style='H5', # Aumentado de Button para H5
            theme_text_color='Custom',
            text_color=get_color_from_hex('#5DADE2'),
            size_hint_y=None,
            height=dp(32),
        ))
        content.add_widget(header)

        # ── Card de Boas-Vindas ──────────────────────────────────────────────
        welcome_card = MDCard(
            orientation='vertical',
            size_hint=(1, None),
            height=dp(120), # Aumentado de 100 para 120
            padding=dp(16),
            radius=[dp(15)],
            md_bg_color=get_color_from_hex('#34495E'), # Azul Marinho Escuro
            elevation=2,
        )
        
        self._lbl_saudacao = MDLabel(
            text='Olá!',
            halign='center',
            font_style='H5', # Aumentado de H6 para H5
            theme_text_color='Custom',
            text_color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(40),
        )
        welcome_card.add_widget(self._lbl_saudacao)
        
        self._lbl_motivacional = MDLabel(
            text='“O movimento é a cura.”',
            halign='center',
            font_style='Subtitle1', # Aumentado de Caption para Subtitle1
            italic=True,
            theme_text_color='Custom',
            text_color=(0.9, 0.9, 0.9, 1),
        )
        welcome_card.add_widget(self._lbl_motivacional)
        
        content.add_widget(welcome_card)

        content.add_widget(MDLabel(
            text='Qual o nosso treino de hoje?',
            halign='center',
            font_style='H6', # Aumentado de Subtitle2 para H6
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(50),
        ))

        # Container dinâmico dos botões
        self._container = MDBoxLayout(
            orientation='vertical',
            spacing=dp(12),
            size_hint_y=None,
        )
        self._container.bind(minimum_height=self._container.setter('height'))
        content.add_widget(self._container)

        self.scroll.add_widget(content)
        root.add_widget(self.scroll)

        # ── rodapé fixo (Barra de Navegação Moderna) ──────────────────────────
        from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
        
        # Usaremos um layout simples com ícones para simular a barra, 
        # para não precisar mudar toda a estrutura da ScreenManager agora.
        rodape = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(85), # Aumentado para comportar duas linhas de texto
            md_bg_color=get_color_from_hex('#1A1A1A'),
            padding=[dp(5), dp(5)],
        )
        
        def _nav_item(icon, text, callback):
            # Layout vertical para ícone + texto
            item = MDBoxLayout(
                orientation='vertical', 
                spacing=0, 
                size_hint_x=1,
                adaptive_height=True,
                pos_hint={'center_y': .5}
            )
            
            btn = MDIconButton(
                icon=icon,
                pos_hint={'center_x': 0.5},
                theme_text_color='Custom',
                text_color=(1, 1, 1, 1),
                on_release=callback
            )
            
            lbl = MDLabel(
                text=text,
                halign='center',
                font_style='Caption',
                theme_text_color='Custom',
                text_color=(1, 1, 1, 1),
                size_hint_y=None,
                height=dp(30), # Aumentado para acomodar duas linhas
                line_height=0.9
            )
            
            item.add_widget(btn)
            item.add_widget(lbl)
            return item

        def _abrir_whatsapp(x):
            import webbrowser
            # Link direto para o seu WhatsApp com uma mensagem inicial opcional
            link = "https://wa.me/5514981428393?text=Olá Ronaldo Medeiros"
            webbrowser.open(link)

        # Ajustamos o texto com quebra de linha e damos mais destaque ao botão de contato
        rodape.add_widget(_nav_item('whatsapp', 'Falar com\nRonaldo', _abrir_whatsapp))
        rodape.add_widget(_nav_item('chart-line', 'Histórico', lambda x: self._abrir_historico_atividade()))
        rodape.add_widget(_nav_item('information-outline', 'Sobre', lambda x: self._abrir_sobre()))

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
        
        # Sorteia uma frase nova toda vez que a tela é carregada
        self._lbl_motivacional.text = f'“{random.choice(FRASES_MOTIVACIONAIS)}”'

    # ── montagem dinâmica ─────────────────────────────────────────────────────

    def _reconstruir_botoes(self):
        try:
            app = MDApp.get_running_app()
            hoje = datetime.now().strftime('%d/%m/%Y')
            
            # Limpa o texto de "Atualizando..." ao reconstruir
            if hasattr(self, '_lbl_motivacional') and "Atualizando" in self._lbl_motivacional.text:
                self._atualizar_saudacao()

            # Garante que treinos seja um dicionário
            import json
            treinos = app.treinos
            if isinstance(treinos, str):
                try: treinos = json.loads(treinos)
                except: treinos = {}
            
            if not isinstance(treinos, dict):
                treinos = {}
                
            letras = sorted(treinos.keys())
            proximo = _proximo_treino(app)

            self._container.clear_widgets()

            if not letras:
                self._container.add_widget(MDLabel(
                    text="Avise Ronaldo Medeiros que seu app já está instalado.\nO seu treino personalizado aparecerá aqui!",
                    halign='center',
                    theme_text_color='Secondary',
                    size_hint_y=None,
                    height=dp(100)
                ))
                return

            for letra in letras:
                nome = app.treinos_nomes.get(letra, '')
                btn  = _BotaoTreino(letra=letra, nome=nome, on_abrir=self._ir)
                data, hora = _ultima_conclusao_treino(app, letra, hoje)
                btn.atualizar_status(data, hora, hoje)
                btn.destacar(letra == proximo)
                self._container.add_widget(btn)
        except Exception as e:
            print(f"Erro ao reconstruir botoes: {e}")

    # ── ações ─────────────────────────────────────────────────────────────────

    def _ir(self, treino):
        app = MDApp.get_running_app()
        tela = app.sm.get_screen('treino')
        tela.carregar(treino)
        app.sm.current = 'treino'

    def _abrir_historico_atividade(self):
        MDApp.get_running_app().sm.current = 'atividade'

    def _abrir_sobre(self):
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
