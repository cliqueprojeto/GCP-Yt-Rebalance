"""Atualizações a partir das releases públicas do GitHub.

Consulta apenas a API de releases do repositório oficial, baixa o instalador
do sistema atual, confere o SHA-256 publicado junto e abre/instala o pacote.
Nenhum dado do usuário é enviado.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen

REPOSITORY = "cliqueprojeto/GCP-Yt-Rebalance"
API_LATEST = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
REPOSITORY_PAGE = f"https://github.com/{REPOSITORY}"
RELEASES_PAGE = f"{REPOSITORY_PAGE}/releases"
USER_AGENT = "GCP-Yt-Rebalance-Updater"
MAX_BYTES = 4 * 1024 ** 3


def parse_version(text):
    numbers = re.findall(r"\d+", str(text or ""))[:3]
    return tuple(int(n) for n in numbers) + (0,) * (3 - len(numbers))


def is_newer(candidate, current):
    return parse_version(candidate) > parse_version(current)


def linux_family(os_release=None):
    """deb, rpm ou arch, a partir de /etc/os-release."""
    if os_release is None:
        try:
            os_release = Path("/etc/os-release").read_text(encoding="utf-8", errors="replace")
        except OSError:
            os_release = ""
    fields = {}
    for line in os_release.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            fields[key.strip()] = value.strip().strip('"').lower()
    ids = " ".join((fields.get("ID", ""), fields.get("ID_LIKE", ""))).split()
    if any(i in ("arch", "manjaro", "endeavouros", "cachyos", "garuda") for i in ids): return "arch"
    if any(i in ("fedora", "rhel", "centos", "suse", "opensuse", "opensuse-leap", "opensuse-tumbleweed", "rocky", "almalinux", "mageia") for i in ids): return "rpm"
    if any(i in ("debian", "ubuntu", "linuxmint", "pop", "elementary", "zorin", "kali", "raspbian") for i in ids): return "deb"
    if shutil.which("pacman"): return "arch"
    if shutil.which("rpm") and not shutil.which("dpkg"): return "rpm"
    return "deb"


def asset_pattern(system=None, machine=None, family=None):
    system = system or sys.platform
    machine = (machine or platform.machine()).lower()
    if system.startswith("win"): return r"Windows-x64-Setup\.exe$"
    if system == "darwin": return r"macOS-arm64\.dmg$" if machine in ("arm64", "aarch64") else r"macOS-x86_64\.dmg$"
    family = family or linux_family()
    return {"deb": r"_amd64\.deb$", "rpm": r"\.x86_64\.rpm$", "arch": r"-x86_64\.pkg\.tar\.zst$"}[family]


def select_asset(assets, pattern):
    by_name = {a.get("name", ""): a for a in assets}
    for name, asset in by_name.items():
        if re.search(pattern, name):
            checksum = by_name.get(name + ".sha256")
            return dict(name=name, url=asset["browser_download_url"], size=int(asset.get("size") or 0),
                        sha256_url=checksum["browser_download_url"] if checksum else None)
    return None


def _get(url, timeout=15):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    return urlopen(request, timeout=timeout)


def check_latest(current_version, release=None):
    """Retorna dados da nova versão ou None quando já está atualizado."""
    if release is None:
        with _get(API_LATEST) as response:
            release = json.loads(response.read(2_000_000).decode("utf-8"))
    if release.get("draft") or release.get("prerelease"):
        return None
    version = str(release.get("tag_name", "")).lstrip("vV")
    if not version or not is_newer(version, current_version):
        return None
    return dict(version=version, notes=(release.get("body") or "").strip(), page=release.get("html_url") or RELEASES_PAGE,
                asset=select_asset(release.get("assets") or [], asset_pattern()))


def download_directory():
    downloads = Path.home() / "Downloads"
    return downloads if downloads.is_dir() else Path(tempfile.gettempdir())


def download(info, progress=None, directory=None):
    asset = info.get("asset")
    if not asset: raise RuntimeError("Nenhum instalador disponível para este sistema.")
    if not asset["url"].startswith("https://github.com/") and not asset["url"].startswith("https://objects.githubusercontent.com/"):
        raise RuntimeError("Origem de download inesperada.")
    expected = None
    if asset.get("sha256_url"):
        with _get(asset["sha256_url"]) as response:
            expected = response.read(4096).decode("utf-8", "replace").split()[0].lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected or ""): raise RuntimeError("Checksum publicado inválido.")
    target_dir = Path(directory or download_directory()); target_dir.mkdir(parents=True, exist_ok=True)
    name = Path(asset["name"]).name
    target = target_dir / name
    partial = target.with_name(name + ".partial")
    digest = hashlib.sha256()
    try:
        with _get(asset["url"], timeout=60) as response, partial.open("wb") as output:
            total = int(response.headers.get("Content-Length") or asset.get("size") or 0)
            done = 0
            while chunk := response.read(1024 * 512):
                done += len(chunk)
                if done > MAX_BYTES: raise RuntimeError("Download maior que o limite permitido.")
                output.write(chunk); digest.update(chunk)
                if progress: progress(done, total)
        if expected and digest.hexdigest() != expected:
            raise RuntimeError("O arquivo baixado não confere com o SHA-256 publicado. Tente novamente.")
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)
    return target


def install(path):
    """Abre ou instala o pacote. Retorna 'quit', 'installed', 'opened' ou 'saved'."""
    path = Path(path)
    name = path.name
    if os.name == "nt":
        subprocess.Popen([str(path)], close_fds=True)
        return "quit"
    if sys.platform == "darwin":
        subprocess.Popen(["/usr/bin/open", str(path)])
        return "opened"
    pkexec = shutil.which("pkexec")
    commands = []
    if name.endswith(".deb"):
        if shutil.which("apt-get"): commands.append(["apt-get", "install", "-y", "--allow-downgrades", str(path)])
        if shutil.which("dpkg"): commands.append(["dpkg", "-i", str(path)])
    elif name.endswith(".rpm"):
        for tool, args in (("dnf", ["install", "-y"]), ("zypper", ["--non-interactive", "install", "--allow-unsigned-rpm"]), ("rpm", ["-U", "--force"])):
            if shutil.which(tool): commands.append([tool, *args, str(path)]); break
    elif name.endswith(".pkg.tar.zst") and shutil.which("pacman"):
        commands.append(["pacman", "-U", "--noconfirm", str(path)])
    if pkexec and commands:
        result = subprocess.run([pkexec, *commands[0]], capture_output=True, timeout=1800)
        if result.returncode == 0: return "installed"
        if result.returncode in (126, 127):  # autenticação cancelada
            return "saved"
        raise RuntimeError(result.stderr.decode(errors="replace")[-600:] or "Falha ao instalar o pacote.")
    opener = shutil.which("xdg-open")
    if opener:
        subprocess.Popen([opener, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "opened"
    return "saved"
