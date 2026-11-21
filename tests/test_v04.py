"""Contratos da versão 0.4: traduções, atualizador e recursos do Apoie."""
from pathlib import Path
import re
import string
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/desktop"))
import i18n
import updater

PIX = ("00020126850014br.gov.bcb.pix0136e474b71b-7491-4eac-992f-632652e5a4eb0223DEV GESTAO CULTURAL PRO"
       "5204000053039865802BR5915BRUNO ALBERTINI6006BRASIL62200516ChromeExtensions63042B27")


class TranslationTests(unittest.TestCase):
    def test_every_literal_key_exists(self):
        source = (ROOT / "apps/desktop/gui.py").read_text(encoding="utf-8")
        keys = set(re.findall(r'\bt\(\s*"([^"]+)"', source)) | set(re.findall(r'set_status\(\s*"([^"]+)"', source))
        keys |= set(re.findall(r'"((?:status|phase|fmt|nav\.group)\.[a-z_.]+)"', source))
        missing = sorted(k for k in keys if k not in i18n.S)
        self.assertEqual(missing, [])

    def test_dynamic_families_are_complete(self):
        for name in ("home", "downloads", "separate", "convert", "queue", "history", "settings", "support", "about"):
            for part in ("eyebrow", "title", "subtitle"): self.assertIn(f"page.{name}.{part}", i18n.S)
            self.assertIn(f"nav.{name}", i18n.S)
        for code in ("both", "instrumental", "vocals", "stems"): self.assertIn(f"op.{code}.text", i18n.S)
        for code in ("audio", "video", "instrumental", "stems"): self.assertIn(f"mode.{code}.text", i18n.S)
        for state in ("waiting", "processing", "done", "error", "cancelled"): self.assertIn(f"state.{state}", i18n.S)
        for fmt in ("wav", "pcm", "flac", "mp3"): self.assertIn(f"fmt.note.{fmt}", i18n.S)
        for kind in ("download", "karaoke", "stems", "convert"): self.assertIn(f"tool.{kind}.text", i18n.S)
        for outcome in ("opened", "installed", "saved"): self.assertIn(f"upd.installed.{outcome}", i18n.S)

    def test_three_languages_with_same_placeholders(self):
        fields = lambda text: sorted(f for _, f, _, _ in string.Formatter().parse(text) if f)
        for key, values in i18n.S.items():
            self.assertEqual(len(values), 3, key)
            if key != "status.raw":
                self.assertTrue(all(v.strip() for v in values), key)
            self.assertEqual(fields(values[0]), fields(values[1]), key)
            self.assertEqual(fields(values[0]), fields(values[2]), key)

    def test_switch_language(self):
        try:
            i18n.set_language("es"); self.assertEqual(i18n.t("nav.queue"), "Cola")
            i18n.set_language("en"); self.assertEqual(i18n.t("app.version", v="1"), "Version 1")
            i18n.set_language("xx"); self.assertEqual(i18n.current(), "pt")
        finally:
            i18n.set_language("pt")


class UpdaterTests(unittest.TestCase):
    ASSETS = [dict(name=n, browser_download_url="https://github.com/x/" + n, size=10) for n in (
        "GCP-Yt-Rebalance-0.5.0-Windows-x64-Setup.exe", "GCP-Yt-Rebalance-0.5.0-Windows-x64-Setup.exe.sha256",
        "GCP-Yt-Rebalance-0.5.0-macOS-arm64.dmg", "GCP-Yt-Rebalance-0.5.0-macOS-x86_64.dmg",
        "gcp-yt-rebalance_0.5.0_amd64.deb", "gcp-yt-rebalance-0.5.0-1.x86_64.rpm",
        "gcp-yt-rebalance-bin-0.5.0-1-x86_64.pkg.tar.zst", "SHA256SUMS.txt")]

    def test_versions(self):
        self.assertTrue(updater.is_newer("v0.10.0", "0.9.9"))
        self.assertFalse(updater.is_newer("0.4.0", "0.4.0"))
        self.assertEqual(updater.parse_version("1.2"), (1, 2, 0))

    def test_asset_per_platform(self):
        pick = lambda **kw: updater.select_asset(self.ASSETS, updater.asset_pattern(**kw))["name"]
        self.assertTrue(pick(system="win32", machine="AMD64").endswith("Setup.exe"))
        self.assertTrue(pick(system="darwin", machine="arm64").endswith("macOS-arm64.dmg"))
        self.assertTrue(pick(system="darwin", machine="x86_64").endswith("macOS-x86_64.dmg"))
        self.assertTrue(pick(system="linux", machine="x86_64", family="deb").endswith(".deb"))
        self.assertTrue(pick(system="linux", machine="x86_64", family="rpm").endswith(".rpm"))
        self.assertTrue(pick(system="linux", machine="x86_64", family="arch").endswith(".pkg.tar.zst"))
        windows = updater.select_asset(self.ASSETS, updater.asset_pattern(system="win32"))
        self.assertTrue(windows["sha256_url"].endswith(".sha256"))

    def test_linux_family(self):
        self.assertEqual(updater.linux_family('ID=linuxmint\nID_LIKE="ubuntu debian"'), "deb")
        self.assertEqual(updater.linux_family("ID=fedora"), "rpm")
        self.assertEqual(updater.linux_family('ID="opensuse-tumbleweed"\nID_LIKE="opensuse suse"'), "rpm")
        self.assertEqual(updater.linux_family("ID=manjaro\nID_LIKE=arch"), "arch")

    def test_check_ignores_old_and_prerelease(self):
        release = dict(tag_name="v99.0.0", body="Notas", html_url="https://github.com", assets=self.ASSETS, prerelease=False)
        info = updater.check_latest("0.4.0", release)
        self.assertEqual(info["version"], "99.0.0")
        self.assertIsNone(updater.check_latest("0.4.0", dict(release, prerelease=True)))
        self.assertIsNone(updater.check_latest("99.0.0", release))


class UpdaterDownloadTests(unittest.TestCase):
    def test_download_verifies_checksum(self):
        import hashlib, io, tempfile
        payload = b"instalador" * 1000
        good = hashlib.sha256(payload).hexdigest()
        class Response(io.BytesIO):
            headers = {"Content-Length": str(len(payload))}
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        def fake(checksum):
            return lambda url, timeout=15: Response((checksum + "  x.exe\n").encode() if url.endswith(".sha256") else payload)
        info = dict(asset=dict(name="x.exe", url="https://github.com/a/x.exe", size=len(payload), sha256_url="https://github.com/a/x.exe.sha256"))
        original = updater._get
        try:
            with tempfile.TemporaryDirectory() as folder:
                updater._get = fake(good)
                seen = []
                path = updater.download(info, lambda done, total: seen.append(done), folder)
                self.assertEqual(path.read_bytes(), payload); self.assertEqual(seen[-1], len(payload))
                updater._get = fake("0" * 64)
                path.unlink()
                with self.assertRaises(RuntimeError): updater.download(info, None, folder)
                self.assertEqual(list(Path(folder).iterdir()), [])
        finally:
            updater._get = original


class SupportAssetsTests(unittest.TestCase):
    def test_pix_payload_and_assets(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from support_assets import crc16
        self.assertEqual(crc16(PIX[:-4]), PIX[-4:])
        gui_source = (ROOT / "apps/desktop/gui.py").read_text(encoding="utf-8")
        self.assertIn("donate.stripe.com/fZu4gzeBSfhbd7451F6Ri00", gui_source)
        self.assertIn("gestaoculturalpro.com.br", gui_source)
        for path in ("assets/support/pix-qr.png", "assets/fonts/Inter-Regular.otf", "assets/fonts/Inter-Bold.otf", "assets/fonts/OFL.txt"):
            self.assertTrue((ROOT / path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
