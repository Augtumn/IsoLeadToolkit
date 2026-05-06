# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all

spec_arg = sys.argv[-1] if sys.argv else ''
spec_path = spec_arg if spec_arg.endswith('.spec') else ''
PROJECT_ROOT = os.path.abspath(os.path.dirname(spec_path)) if spec_path and os.path.isfile(spec_path) else os.path.abspath(os.getcwd())

# Build: python -m PyInstaller build.spec

datas = [('locales', 'locales')]
binaries = []
hiddenimports = [
    'sklearn.utils._cython_blas',
    'sklearn.neighbors.typedefs',
    'sklearn.neighbors.quad_tree',
    'sklearn.tree._utils',
    'scipy.special.cython_special',
    'scipy.spatial.transform._rotation_groups',
    'originpro',
]

excludes = [
    'matplotlib.tests',
    'matplotlib.testing',
    'numpy.tests',
    'pandas.tests',
    'scipy.tests',
    'scipy.testing',
    'sklearn.tests',
    'sklearn.utils.tests',
    'sklearn.metrics.tests',
    'seaborn.tests',
    'seaborn.testing',
    'mpl_toolkits.tests',
    'PIL.tests',
    'PyQt5.QtTest',
]


def _filter_test_datas(items):
    filtered = []
    for src, dest in items:
        src_norm = src.replace('\\', '/').lower()
        if '/tests/' in src_norm:
            continue
        if '/testing/' in src_norm:
            continue
        filtered.append((src, dest))
    return filtered

# Collect all necessary files for complex packages
for pkg in (
    'numpy',
    'umap',
    'sklearn',
    'pandas',
    'matplotlib',
    'seaborn',
    'scipy',
    'openpyxl',
    'xlsxwriter',
    'python_calamine',
    'xgboost',
    'imblearn',
):
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

datas = _filter_test_datas(datas)

block_cipher = None

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'main.py')],
    pathex=[PROJECT_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name='IsotopesAnalyse',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='IsotopesAnalyse',
)
