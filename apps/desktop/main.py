"""Entrada da interface e dos workers isolados do GCP Yt Rebalance."""
import json
import os
from pathlib import Path
import subprocess
import sys
from runtime import BASE, PRODUCT, VERSION
from platform_support import HIDDEN


def launch():
    import ctypes
    if os.name == "nt":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GestaoCulturalPro.GCPYtRebalance")
        except OSError:
            pass
    import customtkinter as ctk
    from customtkinter.windows.widgets.core_rendering import DrawEngine
    DrawEngine.preferred_drawing_method = "polygon_shapes"
    from gui import App, NAV
    root = ctk.CTk()
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        report = Path(sys.argv[2]).resolve()
        def checkpoint(stage):
            report.parent.mkdir(parents=True,exist_ok=True)
            report.with_suffix(".progress.json").write_text(json.dumps(dict(stage=stage)),encoding="utf-8")
        checkpoint("GUI initialized")
        root.withdraw()
        try:
            import hashlib
            import numpy
            import torch
            import soundfile
            import demucs.htdemucs
            from runtime import ffmpeg, MODEL_SHA256
            checkpoint("ML imports passed")
            app = App(root, state_dir=report.parent / "self-test-state", testing=True)
            root.withdraw()
            root.update()
            sizes = []
            for width, height in ((880,600),(1024,640),(1180,780),(1440,900)):
                checkpoint(f"layout {width}x{height}")
                root.geometry(f"{width}x{height}")
                root.deiconify()
                root.update()
                for page in NAV:
                    app.page(page)
                    root.update_idletasks()
                    assert app.bottom.winfo_y()+app.bottom.winfo_height() <= root.winfo_height(), (page,width,height,"footer")
                    assert app.scroll.winfo_height() > 80
                    assert app.footer.winfo_rooty()+app.footer.winfo_height() <= root.winfo_rooty()+root.winfo_height()
                sizes.append([width,height])
            checkpoint("layout passed")
            root.withdraw()
            app.url.set("ftp://invalid.example/video")
            app.enqueue_download()
            assert app.dialogs[-1]["title"] == "Não foi possível adicionar o download"
            gui_flow=False
            fixture=report.parent/"fixture.wav"
            if fixture.is_file():
                checkpoint("GUI queue conversion")
                import time
                app.files=[str(fixture.resolve())]
                app.destination.set(str(report.parent))
                app.operation.set("Somente converter")
                app.enqueue_local()
                deadline=time.monotonic()+90
                while time.monotonic()<deadline:
                    root.update()
                    if app.queue and app.queue[-1]["state"] in ("Concluído","Erro"): break
                    time.sleep(.03)
                assert app.queue[-1]["state"]=="Concluído", app.dialogs
                assert app.history[-1]["destination"]
                opened=[]
                import gui
                original_open=gui.open_directory
                try:
                    gui.open_directory=lambda path:opened.append(str(path))
                    app.page("Histórico")
                    app.open_folder(app.history[-1]["destination"])
                    assert opened==[str(Path(app.history[-1]["destination"]))]
                finally:
                    gui.open_directory=original_open
                gui_flow=True
            checkpoint("queue and history passed")
            from preferences import quality_defaults
            app.format.set("MP3"); app.bits.set("24"); app.rate.set("48000"); app.bitrate.set("320"); app.threads.set("4"); app.resolution.set("1080p")
            app.save_settings()
            expected=dict(app.saved_quality)
            app.format.set("WAV"); app.bits.set("16"); app.save_settings(quiet=True)
            app.load_settings()
            assert {key:getattr(app,key).get() for key in expected}==expected
            original_history=list(app.history)
            app.restore_factory_settings()
            assert app.saved_quality==quality_defaults() and app.bits.get()=="16" and app.history==original_history
            app.url.set("https://www.youtube.com/watch?v=own-test")
            app.metadata=dict(url=app.url.get(),title="Teste local de opções",duration=1,video_available=True,resolutions=[360],playlist=[],subtitles=[dict(language="pt",name="Português",automatic=False),dict(language="en",name="English",automatic=True)])
            app.page("Downloads"); root.update_idletasks()
            assert set(app.subtitle_selection)=={(False,"pt"),(True,"en")}
            checkpoint("preferences and subtitles UI passed")
            assert hashlib.sha256((BASE/"models/weights/955717e8.safetensors").read_bytes()).hexdigest() == MODEL_SHA256
            tools = {}
            for name in ("ffmpeg","ffprobe"):
                result = subprocess.run([str(ffmpeg(name)),"-version"],capture_output=True,timeout=30,creationflags=HIDDEN)
                assert result.returncode == 0
                tools[name] = result.stdout.decode(errors="replace").splitlines()[0]
            from runtime import download_tool
            downloader = subprocess.run([str(download_tool("yt-dlp")),"--version"],capture_output=True,timeout=45,creationflags=HIDDEN)
            assert downloader.returncode == 0
            tools["yt-dlp"] = downloader.stdout.decode().strip()
            result = dict(status="passed",product=PRODUCT,version=VERSION,frozen=bool(getattr(sys,"frozen",False)),
                torch=torch.__version__,numpy=numpy.__version__,soundfile=soundfile.__version__,models_verified=True,
                pages_constructed=len(NAV),tested_layout_sizes=sizes,custom_error_dialog=True,gui_queue_conversion=gui_flow,
                history_open_routing=gui_flow,tools=tools)
            result.update(preferences_save_reload=True,factory_reset_preserves_history=True,subtitle_selection_ui=True)
            code = 0
        except Exception as error:
            import traceback
            result = dict(status="failed",error=str(error),traceback=traceback.format_exc())
            code = 1
        report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        root.destroy()
        return code
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    if len(sys.argv)==3 and sys.argv[1]=="--worker":
        from engine import worker
        raise SystemExit(worker(sys.argv[2]))
    try:
        code=launch()
    except Exception:
        if len(sys.argv)==3 and sys.argv[1]=="--self-test":
            import traceback
            path=Path(sys.argv[2]); path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(dict(status="failed",traceback=traceback.format_exc()),ensure_ascii=False),encoding="utf-8")
            code=1
        else:
            raise
    raise SystemExit(code)
