import os
import platform as py_platform
import json
import threading
import uuid
from datetime import datetime

# Configurações de Ambiente para Vídeo e Gráficos
if py_platform.system() == 'Windows':
    os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivymd.app import MDApp
from kivy.uix.label import Label
from kivy.utils import platform as kivy_platform

# Forçar player nativo no Android para resolver fundo cinza logo no início
if kivy_platform == 'android':
    os.environ['KIVY_VIDEO'] = 'android'


def _pasta_downloads():
    if kivy_platform == 'android':
        return '/storage/emulated/0/Download'
    return os.path.join(os.path.expanduser('~'), 'Downloads')

class RonaldoMedeirosFisiologistaApp(MDApp):
    def build(self):
        try:
            self.title = 'Ronaldo Medeiros'
            self.theme_cls.primary_palette = 'BlueGray'
            self.theme_cls.theme_style = 'Dark'

            # Define o diretório de dados apenas quando o app está pronto
            self.data_dir = self.user_data_dir
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Inicializa caminhos
            self.treinos_file       = os.path.join(self.data_dir, 'treinos.json')
            self.treinos_nomes_file = os.path.join(self.data_dir, 'treinos_nomes.json')
            self.historico_file     = os.path.join(self.data_dir, 'historico.json')
            self.atividade_file     = os.path.join(self.data_dir, 'historico_atividade.json')
            self.cliente_file       = os.path.join(self.data_dir, 'cliente.json')
            self.sync_file          = os.path.join(self.data_dir, 'ultima_sync.json')
            self._CLIENTE_BACKUP    = os.path.join(_pasta_downloads(), 'ronaldo_cliente_backup.json')

            # Registro de Fonte (Silencioso se falhar)
            try:
                font_path = os.path.join(os.path.dirname(__file__), 'assets', 'fonts', 'ERASBD.TTF')
                if os.path.exists(font_path):
                    LabelBase.register(name='ErasBoldITC', fn_regular=font_path)
            except: pass

            self.pode_editar      = True
            self.treino_atual     = ''
            self.progresso_treino = {}
            
            # Carregamento de dados (Seguro)
            self.cliente       = self._carregar(self.cliente_file, None) or self._recuperar_cliente_downloads()
            self.treinos       = self._carregar(self.treinos_file,       {})
            self.treinos_nomes = self._carregar(self.treinos_nomes_file, {})
            self.historico     = self._carregar(self.historico_file,     {})
            self.atividade     = self._carregar(self.atividade_file,     [])

            # Importação tardia das telas para evitar crash no loading pesado
            from telas.tela_cadastro import TelaCadastro
            from telas.tela_home import TelaHome
            from telas.tela_treino import TelaTreino
            from telas.tela_historico import TelaHistorico
            from telas.tela_atividade import TelaAtividade

            self.sm = ScreenManager(transition=SlideTransition())
            self.sm.add_widget(TelaCadastro(name='cadastro'))
            self.sm.add_widget(TelaHome(name='home'))
            self.sm.add_widget(TelaTreino(name='treino'))
            self.sm.add_widget(TelaHistorico(name='historico'))
            self.sm.add_widget(TelaAtividade(name='atividade'))

            # Decisão de tela inicial
            if self.cliente:
                self.sm.current = 'home'
            else:
                self.sm.current = 'cadastro'
                
            return self.sm

        except Exception as e:
            # Em caso de erro grave, mostra uma tela branca com o erro
            return Label(text=f"Erro de Inicializacao:\n{str(e)}", color=(1,0,0,1))

    def on_start(self):
        if hasattr(self, 'cliente') and self.cliente:
            import firebase_sync
            threading.Thread(target=self._puxar_treinos_firebase, daemon=True).start()

    def _carregar(self, path, default):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except: pass
        return default

    def _recuperar_cliente_downloads(self):
        try:
            dados = self._carregar(self._CLIENTE_BACKUP, None)
            if dados and dados.get('id'):
                cliente = {'id': dados['id'], 'nome': dados['nome']}
                with open(self.cliente_file, 'w', encoding='utf-8') as f:
                    json.dump(cliente, f)
                return cliente
        except: pass
        return None

    def salvar(self, treino=None, exercicios_concluidos=None, on_success=None, on_error=None):
        agora = datetime.now()
        data_str = agora.strftime('%d/%m/%Y')
        hora_str = agora.strftime('%H:%M:%S')

        if treino and exercicios_concluidos:
            for ex in exercicios_concluidos:
                self.atividade.append({
                    'data':         data_str,
                    'hora':         hora_str,
                    'treino':       treino,
                    'ex_id':        ex['id'],
                    'nome':         ex['nome'],
                    'series_total': ex.get('series', ''),
                    'peso':         ex.get('peso', ''),
                    'concluido':    True,
                })
            try:
                with open(self.atividade_file, 'w', encoding='utf-8') as f:
                    json.dump(self.atividade, f, ensure_ascii=False, indent=2)
            except: pass

        try:
            with open(self.treinos_file, 'w', encoding='utf-8') as f:
                json.dump(self.treinos, f, ensure_ascii=False, indent=2)
            with open(self.historico_file, 'w', encoding='utf-8') as f:
                json.dump(self.historico, f, ensure_ascii=False, indent=2)
            
            if self.cliente:
                import firebase_sync
                # Salva atividade e histórico
                firebase_sync.salvar_dados(
                    self.cliente['id'], 
                    self.historico, 
                    self.atividade, 
                    None,
                    on_success=on_success,
                    on_error=on_error
                )
            elif on_success:
                on_success()
        except Exception as e:
            if on_error:
                on_error(str(e))

    def _puxar_treinos_firebase(self):
        try:
            import firebase_sync
            dados = firebase_sync.buscar_cliente_completo(self.cliente['id'])
            if dados and (dados.get('trainer_editou') or not self.treinos):
                self.treinos = dados['treinos']
                self.treinos_nomes = dados['treinos_nomes']
                with open(self.treinos_file, 'w', encoding='utf-8') as f:
                    json.dump(self.treinos, f, ensure_ascii=False)
                Clock.schedule_once(lambda dt: self.sm.get_screen('home')._reconstruir_botoes() if self.sm.has_screen('home') else None)
        except: pass

if __name__ == '__main__':
    RonaldoMedeirosFisiologistaApp().run()
