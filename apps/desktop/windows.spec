# PyInstaller: aplicação em diretório para instalação, sem extração a cada tarefa.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

root = Path(SPECPATH).resolve().parents[1]
datas = [
    (str(root / 'assets/branding'), 'assets/branding'),
    (str(root / 'models/weights/955717e8.safetensors'), 'models/weights'),
    (str(root / 'vendor/ffmpeg'), 'vendor/ffmpeg'),
    (str(root / 'vendor/notices'), 'vendor/notices'),
    (str(root / 'vendor/download'), 'vendor/download'),
]
datas += collect_data_files('customtkinter')
datas += collect_data_files('demucs', include_py_files=True)
datas += collect_data_files('julius', include_py_files=True)
for package in ('demucs', 'einops', 'julius', 'safetensors', 'soundfile'):
    datas += copy_metadata(package)

analysis = Analysis([str(root / 'apps/desktop/main.py')],
    pathex=[str(root / 'apps/desktop')], binaries=[], datas=datas,
    hiddenimports=['demucs.htdemucs', 'demucs.hf', 'demucs.apply', 'safetensors.torch', 'soundfile'],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['onnx', 'onnxruntime', 'matplotlib', 'pandas', 'scipy', 'tensorflow', 'pytest', 'IPython'],
    noarchive=False)
archive = PYZ(analysis.pure)
exe = EXE(archive, analysis.scripts, [], exclude_binaries=True,
    name='GCP Yt Rebalance', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
    version=str(root / 'apps/desktop/windows-version.txt'),
    icon=str(root / 'assets/branding/taskbar.ico'))
distribution = COLLECT(exe, analysis.binaries, analysis.datas, strip=False, upx=False, name='GCP Yt Rebalance')
