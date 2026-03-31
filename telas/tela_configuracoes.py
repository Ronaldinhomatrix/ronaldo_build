from kivy.metrics import dp
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

        content.add_widget(MDLabel(
            text='Desenvolvido por',
            halign='center',
            font_style='Subtitle1',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(32),
        ))
        content.add_widget(MDLabel(
            text='[color=#FFFFFF]Operant[/color][color=#5b9cf6]Lab[/color]',
            markup=True,
            halign='center',
            font_name='ErasBoldITC',
            font_style='H4',
            theme_text_color='Custom',
            text_color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(52),
        ))

        content.add_widget(MDBoxLayout(size_hint_y=1))

        root.add_widget(content)
        self.add_widget(root)

    # ── navegação ─────────────────────────────────────────────────────────────

    def _voltar(self):
        MDApp.get_running_app().sm.current = 'home'
