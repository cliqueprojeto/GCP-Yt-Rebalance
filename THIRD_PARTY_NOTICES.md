# Componentes de terceiros

GCP Yt Rebalance é distribuído sob a [GPL-3.0-or-later](LICENSE). Os instaladores incluem os componentes abaixo, cada um sob sua própria licença. Os textos completos acompanham o pacote em `vendor/notices` (gerados no build a partir das fontes fixadas em `scripts/native-sources.lock.json`).

| Componente | Uso | Licença |
|---|---|---|
| [Python](https://www.python.org) | Runtime embarcado | PSF License |
| [PyTorch](https://pytorch.org) | Execução do modelo na CPU | BSD-3-Clause |
| [Demucs / HTDemucs](https://github.com/facebookresearch/demucs) | Separação de voz e instrumentos (código e pesos) | MIT |
| [julius](https://github.com/adefossez/julius), [einops](https://github.com/arogozhnikov/einops), [safetensors](https://github.com/huggingface/safetensors) | Dependências do motor | MIT / Apache-2.0 |
| [NumPy](https://numpy.org) | Processamento numérico | BSD-3-Clause |
| [soundfile](https://github.com/bastibe/python-soundfile) / libsndfile | Leitura e gravação de áudio | BSD-3-Clause / LGPL-2.1 |
| [FFmpeg](https://ffmpeg.org) + [LAME](https://lame.sourceforge.io) | Decodificação, conversão e MP3 | LGPL-2.1-or-later |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Downloads | Unlicense |
| [Node.js](https://nodejs.org) | Runtime JavaScript usado pelo downloader | MIT |
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), [darkdetect](https://github.com/albertosottile/darkdetect) | Interface | MIT / BSD-3-Clause |
| [Pillow](https://python-pillow.org) | Ícones e ilustrações | MIT-CMU |
| [Tcl/Tk](https://www.tcl.tk) | Toolkit gráfico | Tcl/Tk License (BSD) |
| [Inter](https://rsms.me/inter/) | Fonte da interface | SIL OFL 1.1 ([texto](assets/fonts/OFL.txt)) |
| [PyInstaller](https://pyinstaller.org) bootloader | Executável | GPL-2.0 com exceção de bootloader |
| [NSIS](https://nsis.sourceforge.io) | Instalador do Windows | zlib/libpng |

As marcas citadas (YouTube, Vimeo, SoundCloud etc.) pertencem aos seus titulares e aparecem apenas como referência de compatibilidade.
