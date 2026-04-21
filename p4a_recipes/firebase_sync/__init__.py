from pythonforandroid.recipe import Recipe
from pythonforandroid.toolchain import current_directory, shprint
from os.path import join, exists
import os
import shutil
import subprocess
import sh


class FirebaseSyncRecipe(Recipe):
    name = 'firebase_sync'
    version = '1.0'
    depends = ['python3', 'setuptools']
    call_hostpython_via_targetpython = False

    def should_build(self, arch):
        site_pkgs = self.ctx.get_site_packages_dir(arch)
        if not exists(site_pkgs):
            return True
        for f in os.listdir(site_pkgs):
            if f.startswith('firebase_sync') and f.endswith('.so'):
                return False
        return True

    def get_build_dir(self, arch):
        arch_str = arch.arch if hasattr(arch, 'arch') else arch
        return join(self.ctx.build_dir, 'other_builds', self.name, arch_str)

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        build_dir = self.get_build_dir(arch.arch)
        os.makedirs(build_dir, exist_ok=True)

        # Step 1: copia .py como .pyx
        shutil.copy(
            join(self.ctx.root_dir, 'firebase_sync.py'),
            join(build_dir, 'firebase_sync.pyx'),
        )

        # Step 2: gera .c com Cython do host (saída é portável, independente de arq)
        cython_bin = shutil.which('cython') or '/home/marcos/.local/bin/cython'
        subprocess.check_call(
            [cython_bin, '--3str', 'firebase_sync.pyx'],
            cwd=build_dir,
        )

        # Step 3: encontra headers Python do Android
        python_include = self._find_python_include(arch)

        # Step 4: compila .c → .so com o cross-compiler do NDK (via env['CC'])
        cc = env.get('CC', 'gcc').split()[0]
        cflags = env.get('CFLAGS', '')
        ldflags = env.get('LDFLAGS', '')
        so_file = join(build_dir, 'firebase_sync.so')

        cmd = (
            f'{cc} -shared -fPIC -O2 '
            f'-I{python_include} '
            f'{cflags} '
            f'{join(build_dir, "firebase_sync.c")} '
            f'-o {so_file} '
            f'{ldflags}'
        )
        subprocess.check_call(cmd, shell=True, env=env, cwd=build_dir)

        # Step 5: instala em site-packages
        site_pkgs = self.ctx.get_site_packages_dir(arch)
        shutil.copy(so_file, join(site_pkgs, 'firebase_sync.so'))

    def _find_python_include(self, arch):
        arch_str = arch.arch if hasattr(arch, 'arch') else arch
        ndk_api = getattr(self.ctx, 'ndk_api', 21)
        candidate = join(
            self.ctx.build_dir,
            'other_builds', 'python3',
            f'{arch_str}__ndk_target_{ndk_api}',
            'python3', 'Include',
        )
        if exists(candidate):
            return candidate
        # fallback: busca Python.h no build_dir
        for root, dirs, files in os.walk(
            join(self.ctx.build_dir, 'other_builds', 'python3')
        ):
            if 'Python.h' in files:
                return root
        raise RuntimeError(f'Python.h não encontrado para {arch_str}')


recipe = FirebaseSyncRecipe()
