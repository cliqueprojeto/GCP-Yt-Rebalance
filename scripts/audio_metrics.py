"""Métricas de paridade de forma de onda, sem alinhamento ou ganho ocultos."""
import numpy as np


def compare(reference, candidate):
    a = np.asarray(reference, dtype=np.float64)
    b = np.asarray(candidate, dtype=np.float64)
    if a.shape != b.shape or a.size == 0:
        raise ValueError("As saídas devem ter exatamente o mesmo shape não vazio.")
    if not (np.isfinite(a).all() and np.isfinite(b).all()):
        raise ValueError("NaN/Inf em saída de áudio.")
    error = a - b
    energy = float(np.sum(a * a))
    noise = float(np.sum(error * error))
    # None representa identidade exata ou sinal de referência silencioso.
    snr = float(10 * np.log10(energy / noise)) if noise > 0 and energy > 0 else None
    return dict(samples=int(a.size), rmse=float(np.sqrt(np.mean(error * error))),
                max_abs_error=float(np.max(np.abs(error))), snr_db=snr,
                exact=bool(np.array_equal(a, b)), silent_reference=energy == 0,
                candidate_peak=float(np.max(np.abs(b))),
                candidate_over_full_scale=int(np.count_nonzero(np.abs(b) > 1)))
