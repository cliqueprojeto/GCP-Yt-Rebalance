"""Downloads via sidecar oficial. Sem cookies, plugins, DRM ou componentes remotos."""
import ipaddress
import json
import math
import os
from pathlib import Path
import shutil
import socket
import subprocess
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from runtime import BASE, ffmpeg, download_tool
from naming import result_folder, output_name

HIDDEN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
HOSTS = ("youtube.com", "youtu.be", "vimeo.com", "soundcloud.com", "archive.org", "commons.wikimedia.org")


def subtitle_options(data):
    tracks=[]
    for field,automatic in (("subtitles",False),("automatic_captions",True)):
        for language,formats in (data.get(field) or {}).items():
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",language) or language=="live_chat": continue
            usable=[item for item in formats if item.get("ext") in ("srt","vtt","ttml","ass","ssa")]
            if usable:
                tracks.append(dict(language=language,name=next((item["name"] for item in usable if item.get("name")),language),automatic=automatic))
    return sorted(tracks,key=lambda item:(item["automatic"],item["name"].casefold(),item["language"]))


def validate_subtitles(selected,available):
    if not isinstance(selected,list) or len(selected)>20:
        raise ValueError("Selecione no máximo 20 idiomas de legenda por tarefa.")
    options={(item["automatic"],item["language"]) for item in available}
    result=[]
    for item in selected:
        if not isinstance(item,dict) or type(item.get("automatic")) is not bool or not isinstance(item.get("language"),str):
            raise ValueError("Seleção de legenda inválida. Carregue as opções novamente.")
        key=(item["automatic"],item["language"])
        if key not in options:
            raise ValueError("O idioma de legenda selecionado não está mais disponível. Carregue as opções novamente.")
        if key not in result: result.append(key)
    return result


def download_subtitles(url,selected,available,work,title):
    from engine import emit
    from naming import safe_name
    selected=validate_subtitles(selected,available)
    attachments=[]
    for index,(automatic,language) in enumerate(selected):
        folder=work/f"subtitle-{index:02d}"; folder.mkdir()
        emit(work,f"Baixando legenda {language}",None,phase_key="subtitles")
        command=base_command()+["--skip-download","--no-playlist","--no-simulate","--quiet",
            "--write-auto-subs" if automatic else "--write-subs",
            "--no-write-subs" if automatic else "--no-write-auto-subs",
            "--sub-langs",re.escape(language),"--sub-format","vtt/srt/best","--convert-subs","srt",
            "-o",str(folder/"subtitle.%(ext)s"),"--",url]
        result=subprocess.run(command,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=120,creationflags=HIDDEN)
        files=list(folder.glob("*.srt"))
        if result.returncode or len(files)!=1 or files[0].stat().st_size==0:
            raise RuntimeError(f"Não foi possível baixar a legenda {language}. A fonte pode ter limitado o acesso. Recarregue as opções ou tente sem este idioma.")
        suffix="_automatica" if automatic else ""
        attachments.append((files[0],f"{safe_name(title,140)}_Legenda_{language}{suffix}.srt"))
    return attachments


def validate_url(value, resolve=False):
    value = value.strip()
    if len(value) > 2048:
        raise ValueError("O link é muito longo.")
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    # Somente o servidor efêmero da suíte automatizada pode usar HTTP local.
    test_server = os.environ.get("GCP_REBALANCE_TEST_SERVER")
    if test_server and value.startswith(test_server + "/") and host == "127.0.0.1":
        return value
    if parsed.scheme != "https" or not host or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Cole um link HTTPS válido, sem usuário ou senha.")
    if host == "spotify.com" or host.endswith(".spotify.com"):
        raise ValueError("Spotify não oferece download de músicas por este aplicativo. Importe uma cópia local autorizada.")
    known = any(host == item or host.endswith("." + item) for item in HOSTS)
    direct = Path(parsed.path).suffix.lower() in {".mp4", ".webm", ".mp3", ".wav", ".flac", ".m4a", ".ogg"}
    if not known and not direct:
        raise ValueError("Fonte ainda não habilitada. Use YouTube, Vimeo, SoundCloud, Archive.org ou um link HTTPS direto de mídia.")
    if resolve:
        try:
            addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        except OSError:
            raise ValueError("Não foi possível localizar o site. Verifique a conexão e o link.") from None
        if any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
            raise ValueError("Endereços de rede local ou reservados não são aceitos.")
    if host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com"):
        query = {key: values[0] for key, values in parse_qs(parsed.query).items() if key in ("v", "list", "index", "t")}
        return urlunparse(("https", host, parsed.path, "", urlencode(query), ""))
    # Tokens de acesso não entram em tarefas/histórico desta versão.
    if any(key.lower() in {"token", "access_token", "auth", "key", "signature", "cookie"} for key in parse_qs(parsed.query)):
        raise ValueError("Este link contém credenciais ou tokens. Use um link público sem credenciais.")
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", parsed.query, ""))


def base_command():
    return [str(download_tool("yt-dlp")), "--ignore-config", "--no-plugin-dirs", "--no-cache-dir",
            "--no-remote-components", "--no-js-runtimes", "--js-runtimes", f"node:{download_tool('node')}",
            "--ffmpeg-location", str(ffmpeg().parent), "--socket-timeout", "20", "--retries", "2", "--fragment-retries", "2",
            "--no-warnings", "--encoding", "utf-8"]


def source_error(text):
    text = text.lower()
    if "private" in text or "sign in" in text or "login" in text or "members" in text or "drm" in text:
        return "A fonte exige acesso privado, autenticação ou proteção não suportada. Use um arquivo local autorizado."
    if "403" in text or "forbidden" in text or "429" in text:
        return "O site recusou o download ou limitou o acesso. Tente mais tarde ou importe o arquivo local."
    if "unsupported url" in text:
        return "Este link não é compatível com a versão atual do downloader."
    if "not available" in text or "unavailable" in text:
        return "O conteúdo está indisponível nesta fonte ou região."
    return "Não foi possível obter a mídia. Verifique o link, a conexão e se a fonte permite download."


def inspect_url(value, work):
    from engine import emit
    url = validate_url(value, resolve=True)
    emit(work, "Buscando informações do link", None, phase_key="inspection")
    playlist = urlparse(url).path.rstrip("/") == "/playlist"
    command = base_command() + (["--flat-playlist", "--playlist-end", "20"] if playlist else ["--no-playlist"])
    result = subprocess.run([*command, "--skip-download", "--dump-single-json", "--", url], capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=120, creationflags=HIDDEN)
    if result.returncode:
        raise RuntimeError(source_error(result.stderr))
    data = json.loads(result.stdout)
    if data.get("entries") is not None:
        entries = [dict(title=item.get("title", "Vídeo"), url=item.get("webpage_url") or item.get("url")) for item in data["entries"] if item]
        return dict(title=data.get("title", "Playlist"), playlist=entries[:20], url=url)
    if data.get("is_live") or data.get("live_status") == "is_live":
        raise ValueError("Transmissões ao vivo não são suportadas. Use um vídeo finalizado.")
    duration = float(data.get("duration") or 0)
    if duration and (not math.isfinite(duration) or duration > 1800):
        raise ValueError("A duração excede o limite de 30 minutos desta versão.")
    formats = [item for item in data.get("formats", []) if not item.get("has_drm")]
    heights = sorted({int(item["height"]) for item in formats if item.get("height") and item.get("vcodec") != "none"})
    return dict(title=data.get("title") or "Mídia", duration=duration, url=url, resolutions=heights,
                audio_available=any(item.get("acodec") not in (None, "none") for item in formats),
                video_available=bool(heights) or data.get("ext") in ("mp4", "webm", "mkv"), playlist=[],subtitles=subtitle_options(data))


def download_task(request, work):
    import engine
    from engine import emit, execute, probe
    url = validate_url(request["url"], resolve=True)
    destination = Path(request["destination"]).resolve(strict=True)
    if not destination.is_dir():
        raise ValueError("Selecione uma pasta de saída válida.")
    if shutil.disk_usage(destination).free < 1024 ** 3:
        raise OSError("É necessário pelo menos 1 GiB livre na pasta de saída.")
    metadata = inspect_url(url, work)
    if metadata.get("playlist"):
        raise ValueError("Selecione um vídeo da playlist antes de adicioná-lo à fila.")
    selected_subtitles=request.get("subtitles",[])
    validate_subtitles(selected_subtitles,metadata.get("subtitles",[]))
    emit(work, "Fonte identificada", 0, title=metadata["title"], duration=metadata.get("duration",0), phase_key="download")
    mode = request.get("download_mode", "audio")
    if mode not in ("audio", "video", "instrumental", "stems"):
        raise ValueError("Modo de download inválido.")
    height = request.get("resolution", 0)
    if type(height) is not int or height < 0 or height > 8640:
        raise ValueError("Resolução inválida.")
    if mode == "video" and not metadata["video_available"]:
        raise ValueError("A fonte não oferece vídeo para este link.")
    cache = work / "download"
    cache.mkdir()
    constraint = f"[height<={height}]" if height else ""
    selector = f"bv*{constraint}+ba/b{constraint}" if mode == "video" else "ba/b"
    command = base_command() + ["--no-playlist", "--no-simulate", "--quiet", "--newline", "--progress", "--no-overwrites",
        "--max-filesize", "2G", "--match-filter", "!is_live", "-f", selector,
        "-o", str(cache / "media.%(ext)s"), "--print", "after_move:GCP_FILE:%(filepath)s",
        "--progress-template", "download:GCP:%(progress.downloaded_bytes)s|%(progress.total_bytes,progress.total_bytes_estimate)s|%(progress.eta)s"]
    if mode == "video":
        command += ["--merge-output-format", "mp4/mkv"]
    with (work / "download-errors.txt").open("w", encoding="utf-8") as errors:
        with subprocess.Popen([*command, "--", url], stdout=subprocess.PIPE, stderr=errors, text=True,
                              encoding="utf-8", errors="replace", creationflags=HIDDEN) as process:
            emit(work, "Baixando mídia", 0, phase_key="download")
            for line in process.stdout:
                if line.startswith("GCP:"):
                    try:
                        downloaded, total, eta = line[4:].strip().split("|")
                        fraction = min(1, int(downloaded) / float(total))
                        remaining = float(eta) if eta not in ("NA", "None") else None
                        emit(work, "Baixando mídia", fraction * 44, eta_seconds=remaining, phase_key="download")
                    except (ValueError, ZeroDivisionError):
                        pass
            code = process.wait()
    if code:
        raise RuntimeError(source_error((work / "download-errors.txt").read_text(encoding="utf-8", errors="replace")))
    files = [path for path in cache.iterdir() if path.is_file() and path.suffix.lower() in (".mp4", ".mkv", ".webm", ".m4a", ".mp3", ".ogg", ".opus", ".flac", ".wav")]
    if len(files) != 1:
        raise RuntimeError("A fonte não entregou um arquivo completo dentro dos limites configurados.")
    media = files[0]
    attachments=download_subtitles(url,selected_subtitles,metadata.get("subtitles",[]),work,metadata["title"])
    if mode == "video":
        # ffprobe também confirma áudio incluído; não publicar vídeo mudo como download completo.
        duration, stream = probe(media)
        final = result_folder(destination, metadata["title"], "video")
        staging = destination / f".gcp-{request['id']}.partial"
        staging.mkdir(exist_ok=False)
        try:
            target = staging / output_name(metadata["title"], "video", media.suffix[1:])
            shutil.copyfile(media, target)
            subtitles=engine.copy_attachments(attachments,staging,work)
            (staging / "relatorio.json").write_text(json.dumps(dict(title=metadata["title"], duration=duration,
                operation="video", file=target.name, audio_codec=stream["codec_name"],subtitles=subtitles), ensure_ascii=False, indent=2), encoding="utf-8")
            staging.rename(final)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        emit(work, "Concluído", 100, destination=str(final), title=metadata["title"])
    else:
        local = dict(request, source=str(media), title=metadata["title"], operation={"audio": "convert", "instrumental": "instrumental", "stems": "stems"}[mode])
        engine.PROGRESS_RANGE = (45, 100)
        try:
            execute(local, work,attachments=attachments)
        finally:
            engine.PROGRESS_RANGE = (0, 100)
    shutil.rmtree(cache, ignore_errors=True)
