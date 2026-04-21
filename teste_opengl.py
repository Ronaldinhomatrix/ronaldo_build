import os

# Tenta forçar o Kivy a usar o motor ANGLE (DirectX)
os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

try:
    from kivy.app import App
    from kivy.uix.button import Button
    
    class TestApp(App):
        def build(self):
            return Button(text='Se voce esta vendo este botao,\no OpenGL funcionou!', font_size='20sp')

    if __name__ == '__main__':
        TestApp().run()
except Exception as e:
    print(f"\nERRO AO INICIAR: {e}")
