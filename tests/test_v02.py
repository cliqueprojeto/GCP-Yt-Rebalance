from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/desktop"))
from naming import output_name, result_folder, safe_name
from download import validate_url, source_error
from gui import duration_label


class V02Tests(unittest.TestCase):
    def test_requested_file_suffixes(self):
        for stem,suffix in (("audio","convertido"),("vocals","Voz"),("instrumental","Instrumental"),("drums","Bateria"),("bass","Baixo"),("other","Outros")):
            self.assertEqual(output_name("Canção original",stem,"WAV"),f"Canção original_{suffix}.wav")

    def test_collision_creates_numbered_folder(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"artifacts/unit-temp") as folder:
            first=result_folder(folder,"Minha música","both")
            self.assertEqual(first.name,"Minha música — Voz e instrumental")
            first.mkdir()
            self.assertEqual(result_folder(folder,"Minha música","both").name,"Minha música — Voz e instrumental (2)")

    def test_names_are_windows_safe(self):
        self.assertEqual(safe_name('Canção: teste/novo?'),"Canção_ teste_novo_")
        self.assertEqual(safe_name("CON"),"_CON")

    def test_reject_unsafe_and_private_sources(self):
        for url in ("file:///secret.mp4","ftp://youtube.com/video","https://user:pass@youtube.com/watch?v=x","https://open.spotify.com/track/test","https://youtube.com.evil.invalid/watch?v=x"):
            with self.assertRaises(ValueError): validate_url(url)
        with patch("download.socket.getaddrinfo",return_value=[(2,1,6,"",("127.0.0.1",443))]):
            with self.assertRaises(ValueError): validate_url("https://youtube.com/watch?v=x",resolve=True)

    def test_frontend_does_not_block_on_dns(self):
        with patch("download.socket.getaddrinfo",side_effect=AssertionError("DNS na UI")):
            self.assertEqual(validate_url("https://www.youtube.com/watch?v=x&utm_source=tracking"),"https://www.youtube.com/watch?v=x")

    def test_errors_and_eta_are_readable(self):
        self.assertIn("recusou",source_error("HTTP Error 403 Forbidden"))
        self.assertEqual(duration_label(65),"~1 min 05 s restantes nesta etapa")
        self.assertIn("Calculando",duration_label(None))
