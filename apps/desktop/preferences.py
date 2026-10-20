"""Padrões explícitos, validação e migração das preferências locais."""
FACTORY_QUALITY = dict(format="WAV", bits="16", rate="44100", bitrate="192", threads="2", resolution="Melhor disponível")
QUALITY_OPTIONS = dict(format=["WAV", "PCM", "FLAC", "MP3"], bits=["16", "24", "32"],
                       rate=["44100", "48000"], bitrate=["128", "192", "256", "320"],
                       threads=["1", "2", "4", "8"], resolution=["Melhor disponível", "360p", "480p", "720p", "1080p", "1440p", "2160p"])


def quality_defaults(value=None):
    value = value if isinstance(value, dict) else {}
    result = {key: str(value.get(key)) if str(value.get(key)) in QUALITY_OPTIONS[key] else default
              for key, default in FACTORY_QUALITY.items()}
    if result["format"] == "FLAC" and result["bits"] == "32":
        result["bits"] = "16"
    return result
