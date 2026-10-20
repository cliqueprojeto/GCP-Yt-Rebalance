from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/desktop"))
from engine import validate
TEMP = Path(__file__).resolve().parents[1] / "artifacts/unit-temp"
TEMP.mkdir(parents=True, exist_ok=True)


class DesktopContracts(unittest.TestCase):
    def test_local_unicode_path_is_accepted_without_shell(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as folder:
            path = Path(folder) / "áudio ' & teste.wav"
            path.touch()
            request = dict(source=str(path), destination=folder, operation="convert", format="WAV",
                           rate=44100, bits=24, bitrate=192, threads=2)
            source, destination = validate(request)
            self.assertEqual(source, path.resolve())
            self.assertEqual(destination, Path(folder).resolve())

    def test_reject_playlist_input_and_incompatible_output(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as folder:
            path = Path(folder) / "media.m3u8"
            path.touch()
            request = dict(source=str(path), destination=folder, operation="convert", format="WAV",
                           rate=44100, bits=24, bitrate=192, threads=2)
            with self.assertRaises(ValueError):
                validate(request)
            wav = Path(folder) / "file.wav"
            wav.touch()
            request.update(source=str(wav), format="FLAC", bits=32)
            with self.assertRaises(ValueError):
                validate(request)
            request.update(format="WAV", bits=16, threads=0)
            with self.assertRaises(ValueError):
                validate(request)

    def test_directory_cannot_be_used_as_media(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as folder:
            request = dict(source=folder, destination=folder, operation="convert", format="WAV",
                           rate=44100, bits=24, bitrate=192, threads=2)
            with self.assertRaises(ValueError):
                validate(request)
