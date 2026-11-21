"""Build nativo macOS/Linux; executar no próprio SO e arquitetura."""
from pathlib import Path
import sys
import shutil
import subprocess
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

root=Path(SPECPATH).resolve().parents[1]
sys.path.insert(0,str(root/'apps/desktop'))
from runtime import VERSION
datas=[(str(root/'assets/branding'),'assets/branding'),
       (str(root/'assets/fonts'),'assets/fonts'),
       (str(root/'assets/support'),'assets/support'),
       (str(root/'models/weights/955717e8.safetensors'),'models/weights'),
       (str(root/'vendor/notices'),'vendor/notices')]
datas+=collect_data_files('customtkinter')
for package in ('demucs','julius'):
    datas+=collect_data_files(package,include_py_files=True)
for package in ('demucs','einops','julius','safetensors','soundfile'):
    datas+=copy_metadata(package)
binaries=[(str(root/'vendor/ffmpeg'/name),'vendor/ffmpeg') for name in ('ffmpeg','ffprobe')]
binaries += [(str(root/'vendor/download/node'),'vendor/download')]
if sys.platform!='darwin':
    binaries += [(str(root/'vendor/download/yt-dlp'),'vendor/download')]
analysis=Analysis([str(root/'apps/desktop/main.py')],pathex=[str(root/'apps/desktop')],
    binaries=binaries,datas=datas,hiddenimports=['demucs.htdemucs','demucs.hf','demucs.apply','safetensors.torch','soundfile'] + (['PIL._tkinter_finder'] if sys.platform=='linux' else []),
    excludes=['onnx','onnxruntime','matplotlib','pandas','scipy','tensorflow','pytest','IPython'],noarchive=False)
archive=PYZ(analysis.pure)
exe=EXE(archive,analysis.scripts,[],exclude_binaries=True,name='GCP Yt Rebalance',
    console=False,strip=False,upx=False,argv_emulation=False)
distribution=COLLECT(exe,analysis.binaries,analysis.datas,strip=False,upx=False,name='GCP Yt Rebalance')
if sys.platform=='darwin':
    app=BUNDLE(distribution,name='GCP Yt Rebalance.app',icon=str(root/'assets/branding/taskbar.icns'),
        bundle_identifier='br.com.gestaoculturalpro.ytrebalance',
        info_plist=dict(CFBundleDisplayName='GCP Yt Rebalance',CFBundleShortVersionString=VERSION,
            CFBundleVersion=VERSION,NSRequiresAquaSystemAppearance=False,NSHighResolutionCapable=True,
            NSHumanReadableCopyright='Desenvolvido por Bruno Albertini — Gestão Cultural Pro'))
    # O sidecar onefile universal contém um arquivo PKG anexado. A redução por
    # lipo durante a coleta de BINARY pode descartá-lo na fatia Intel.
    # Copiar após BUNDLE preserva o executável completo; reassinar o bundle em
    # seguida inclui esse código na verificação de integridade já existente.
    sidecar=Path(app.name)/'Contents/Frameworks/vendor/download/yt-dlp'
    sidecar.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(root/'vendor/download/yt-dlp',sidecar)
    sidecar.chmod(0o755)
    subprocess.run(['codesign','--force','--deep','--sign','-',app.name],check=True)
