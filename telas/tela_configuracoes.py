from kivy.metrics import dp
from kivy.uix.image import Image as KivyImage
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.toolbar import MDTopAppBar


class TelaConfiguracoes(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation='vertical')

        root.add_widget(MDTopAppBar(
            title='Sobre',
            left_action_items=[['arrow-left', lambda x: self._voltar()]],
        ))

        content = MDBoxLayout(
            orientation='vertical',
            padding=dp(24),
            spacing=dp(8),
        )

        content.add_widget(MDBoxLayout(size_hint_y=1))

        logo_row = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(80),
        )
        logo_row.add_widget(MDBoxLayout(size_hint_x=1))
        logo_row.add_widget(KivyImage(
            source='Logo_Marca.jpg',
            size_hint=(None, None),
            size=(dp(220), dp(80)),
            allow_stretch=True,
            keep_ratio=True,
        ))
        logo_row.add_widget(MDBoxLayout(size_hint_x=1))
        content.add_widget(logo_row)

        content.add_widget(MDLabel(
            text='operantlab@operantlab.com.br',
            halign='center',
            font_style='Caption',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(24),
        ))

        # Exibe o ID do Cliente para conferência no Painel
        app = MDApp.get_running_app()
        cliente_id = app.cliente['id'] if app.cliente else 'Não identificado'
        content.add_widget(MDLabel(
            text=f'ID: {cliente_id}',
            halign='center',
            font_style='Caption',
            theme_text_color='Hint',
            size_hint_y=None,
            height=dp(20),
        ))

        content.add_widget(MDBoxLayout(size_hint_y=1))

        root.add_widget(content)
        self.add_widget(root)

    # ── navegação ─────────────────────────────────────────────────────────────

    def _voltar(self):
        MDApp.get_running_app().sm.current = 'home'
