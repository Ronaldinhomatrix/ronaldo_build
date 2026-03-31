from collections import OrderedDict
from datetime import datetime, timedelta

from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.toolbar import MDTopAppBar

FILTROS = [
    ('semana', 'Última semana'),
    ('mes',    'Último mês'),
    ('tudo',   'Tudo'),
]

COR_ATIVO   = (0.13, 0.46, 0.87, 1.0)   # azul primário
COR_INATIVO = (0.22, 0.22, 0.22, 1.0)   # cinza escuro


class TelaAtividade(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._filtro = 'semana'
        self._btns_filtro = {}
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation='vertical')

        root.add_widget(MDTopAppBar(
            title='Histórico de Treinos',
            left_action_items=[['arrow-left', lambda x: self._voltar()]],
        ))

        # ── filtros ───────────────────────────────────────────────────────────
        barra = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(52),
            padding=[dp(10), dp(8)],
            spacing=dp(8),
        )
        for codigo, texto in FILTROS:
            btn = MDCard(
                size_hint=(1, None),
                height=dp(36),
                radius=[dp(18)],
                ripple_behavior=True,
                md_bg_color=COR_ATIVO if codigo == self._filtro else COR_INATIVO,
            )
            btn.add_widget(MDLabel(
                text=texto,
                halign='center',
                font_style='Button',
                size_hint_y=1,
            ))
            btn.bind(on_release=lambda x, c=codigo: self._mudar_filtro(c))
            self._btns_filtro[codigo] = btn
            barra.add_widget(btn)
        root.add_widget(barra)

        # ── lista ─────────────────────────────────────────────────────────────
        scroll = ScrollView()
        self._lista = MDBoxLayout(
            orientation='vertical',
            spacing=dp(6),
            padding=[dp(12), dp(4), dp(12), dp(16)],
            size_hint_y=None,
        )
        self._lista.bind(minimum_height=self._lista.setter('height'))
        scroll.add_widget(self._lista)
        root.add_widget(scroll)

        self.add_widget(root)

    # ── ciclo de vida ─────────────────────────────────────────────────────────

    def on_enter(self, *args):
        self._renderizar()

    # ── filtro ────────────────────────────────────────────────────────────────

    def _mudar_filtro(self, filtro):
        self._filtro = filtro
        for codigo, btn in self._btns_filtro.items():
            btn.md_bg_color = COR_ATIVO if codigo == filtro else COR_INATIVO
        self._renderizar()

    # ── renderização ──────────────────────────────────────────────────────────

    def _renderizar(self):
        self._lista.clear_widgets()
        app = MDApp.get_running_app()

        # Define limite de data
        agora = datetime.now()
        if self._filtro == 'semana':
            limite = agora - timedelta(days=7)
        elif self._filtro == 'mes':
            limite = agora - timedelta(days=30)
        else:
            limite = None

        # Coleta registros concluídos dentro do período
        registros = []
        for reg in app.atividade:
            if not reg.get('concluido'):
                continue
            try:
                dt = datetime.strptime(
                    f"{reg['data']} {reg['hora']}", '%d/%m/%Y %H:%M:%S'
                )
            except (ValueError, KeyError):
                continue
            if limite and dt < limite:
                continue
            registros.append((dt, reg))

        if not registros:
            self._lista.add_widget(MDLabel(
                text='Nenhum treino registrado neste período.',
                halign='center',
                theme_text_color='Secondary',
                size_hint_y=None,
                height=dp(100),
            ))
            return

        # Ordena mais recente primeiro
        registros.sort(key=lambda x: x[0], reverse=True)

        # Agrupa por (data, treino) mantendo ordem
        grupos = OrderedDict()
        for dt, reg in registros:
            chave = (reg['data'], reg.get('treino', '?'))
            if chave not in grupos:
                grupos[chave] = []
            grupos[chave].append((dt, reg))

        # Renderiza grupos
        for (data, treino), itens in grupos.items():
            hora_inicio = min(i[0] for i in itens).strftime('%H:%M')
            self._lista.add_widget(self._cabecalho(data, treino, hora_inicio))
            for dt, reg in itens:
                self._lista.add_widget(self._linha_exercicio(dt, reg))

    def _cabecalho(self, data, treino, hora_inicio):
        row = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(34),
            padding=[dp(4), dp(4), dp(4), 0],
            spacing=dp(8),
        )
        row.add_widget(MDLabel(
            text=data,
            font_style='Caption',
            theme_text_color='Secondary',
            size_hint_x=None,
            width=dp(90),
        ))
        row.add_widget(MDLabel(
            text=f'Treino {treino}',
            font_style='Subtitle2',
            bold=True,
            size_hint_x=1,
        ))
        row.add_widget(MDLabel(
            text=hora_inicio,
            font_style='Caption',
            theme_text_color='Secondary',
            halign='right',
            size_hint_x=None,
            width=dp(50),
        ))
        return row

    def _linha_exercicio(self, dt, reg):
        card = MDCard(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(52),
            padding=[dp(12), dp(6), dp(12), dp(6)],
            spacing=dp(8),
            md_bg_color=(0.10, 0.10, 0.10, 1.0),
        )

        # Ícone de check
        card.add_widget(MDLabel(
            text='✓',
            theme_text_color='Custom',
            text_color=(0.22, 0.70, 0.29, 1),
            size_hint_x=None,
            width=dp(24),
            halign='center',
            font_style='H6',
        ))

        # Nome do exercício
        info = MDBoxLayout(orientation='vertical', size_hint_x=1)
        info.add_widget(MDLabel(
            text=reg.get('nome', '—'),
            font_style='Body2',
            size_hint_y=None,
            height=dp(22),
        ))
        info.add_widget(MDLabel(
            text=f"{reg.get('series_total', '?')} séries  •  {reg.get('peso', '?')} kg",
            font_style='Caption',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(18),
        ))
        card.add_widget(info)

        # Horário
        card.add_widget(MDLabel(
            text=dt.strftime('%H:%M'),
            font_style='Caption',
            theme_text_color='Secondary',
            halign='right',
            size_hint_x=None,
            width=dp(40),
        ))

        return card

    # ── navegação ─────────────────────────────────────────────────────────────

    def _voltar(self):
        MDApp.get_running_app().sm.current = 'home'
