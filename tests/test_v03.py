from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/desktop"))
from preferences import quality_defaults
from download import subtitle_options, validate_subtitles, download_subtitles
from engine import copy_attachments


class V03Tests(unittest.TestCase):
    def test_factory_wav16_and_invalid_preferences(self):
        self.assertEqual(quality_defaults()["bits"],"16")
        self.assertEqual(quality_defaults({"format":"FLAC","bits":32})["bits"],"16")
        self.assertEqual(quality_defaults(["invalid"]),quality_defaults())
        self.assertEqual(quality_defaults({"rate":48000,"threads":4})["threads"],"4")

    def test_caption_options_no_urls_or_chat(self):
        result=subtitle_options(dict(subtitles={"pt":[dict(ext="vtt",name="Português",url="https://secret/token")],"live_chat":[dict(ext="vtt")],"../en":[dict(ext="srt")]},automatic_captions={"en":[dict(ext="vtt",name="English")]}))
        self.assertEqual(len(result),2)
        self.assertNotIn("url",result[0])
        self.assertFalse(result[0]["automatic"])
        self.assertTrue(result[1]["automatic"])
        self.assertEqual(validate_subtitles([dict(language="pt",automatic=False)],result),[(False,"pt")])
        for selection in ([dict(language="pt.*",automatic=False)],[dict(language="pt",automatic=0)],[dict(language="de",automatic=True)],[{}]*21):
            with self.assertRaises(ValueError): validate_subtitles(selection,result)

    def test_automatic_caption_command_is_explicit(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"artifacts/unit-temp") as folder:
            work=Path(folder)
            def run(command,**kwargs):
                output=Path(command[command.index("-o")+1]).parent
                (output/"subtitle.en.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nOwn test\n")
                self.assertIn("--write-auto-subs",command)
                self.assertIn("--no-write-subs",command)
                self.assertEqual(command[command.index("--sub-langs")+1],"en")
                return type("Result",(),dict(returncode=0))()
            with patch("download.subprocess.run",side_effect=run):
                result=download_subtitles("https://youtube.com/watch?v=x",[dict(language="en",automatic=True)],[dict(language="en",automatic=True)],work,"My song")
            self.assertEqual(result[0][1],"My song_Legenda_en_automatica.srt")
            stage=work/"stage"; stage.mkdir()
            self.assertEqual(copy_attachments(result,stage,work)[0]["file"],result[0][1])
            with self.assertRaises(ValueError): copy_attachments([(result[0][0],"../bad.srt")],stage,work)
