from pythonforandroid.recipe import Recipe
from pythonforandroid.toolchain import current_directory, shprint
from os.path import join, exists
import os
import shutil
import sh


class FirebaseSyncRecipe(Recipe):
    name = 'firebase_sync'
    version = '1.0'
    depends = ['python3', 'setuptools']
    call_hostpython_via_targetpython = False

    def should_build(self, arch):
        site_pkgs = self.ctx.get_site_packages_dir(arch)
        for f in os.listdir(site_pkgs) if exists(site_pkgs) else []:
            if f.startswith('firebase_sync') and f.endswith('.so'):
                return False
        return True

    def get_build_dir(self, arch):
        return join(self.ctx.build_dir, 'other_builds', self.name, arch)

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        build_dir = self.get_build_dir(arch.arch)
        os.makedirs(build_dir, exist_ok=True)

        # Copiar fonte e renomear para .pyx
        src = join(self.ctx.root_dir, 'firebase_sync.py')
        shutil.copy(src, join(build_dir, 'firebase_sync.pyx'))

        # Escrever setup.py
        with open(join(build_dir, 'setup.py'), 'w') as f:
            f.write(
                'from setuptools import setup\n'
                'from Cython.Build import cythonize\n'
                'setup(ext_modules=cythonize(["firebase_sync.pyx"]))\n'
            )

        with current_directory(build_dir):
            hostpython = sh.Command(self.ctx.hostpython)
            shprint(hostpython, 'setup.py', 'build_ext', '--inplace', _env=env)

        # Instalar .so em site-packages
        site_pkgs = self.ctx.get_site_packages_dir(arch)
        for f in os.listdir(build_dir):
            if f.startswith('firebase_sync') and f.endswith('.so'):
                shutil.copy(join(build_dir, f), join(site_pkgs, f))
                break


recipe = FirebaseSyncRecipe()
