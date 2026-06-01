"""
VROOMM Exposure Time Calculator — Flask backend.

Serves the ETC page and provides a /compute API endpoint that returns
SNR curves for the requested instrument / exposure parameters.

Physics
-------
Signal model (per resolution element):
    N_phot = ZP_flux * Area * 10^(-mag/2.5) * throughput * Δλ * t_exp
    where Δλ = λ₀ / R  (resolution element width in Angstroms)

For n_sub sub-exposures of duration t_sub = t_total / n_sub:
    N_phot_total = N_phot(t_sub) × n_sub  ==  N_phot(t_total)

Noise variance (per resolution element):
    σ² = N_phot_total                          (shot noise)
       + CIC × spatial_pix × n_sub            (clock-induced charges)
       + dark × spatial_pix × t_total         (dark current)

SNR = N_phot_total / σ
"""

from __future__ import annotations

import json
import math
import os

import numpy as np
import yaml
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

# Physical constants
_H_ERG_S = 6.62607015e-27      # Planck constant (erg·s)
_C_CM_S  = 2.99792458e10       # Speed of light (cm/s)
_C_KM_S  = 2.99792458e5        # Speed of light (km/s)


def load_config() -> dict:
    with open(_CONFIG_PATH) as fh:
        return yaml.safe_load(fh)


def photons_per_resel(
    mag: np.ndarray,
    exptime_s: float | np.ndarray,
    cfg: dict,
) -> np.ndarray:
    """Return photon count per resolution element for each magnitude."""
    mag = np.asarray(mag, dtype=float)
    area_cm2 = math.pi * (cfg["telescope"]["primary_diameter_cm"] / 2.0) ** 2
    wave0_a  = cfg["instrument"]["central_wavelength_a"]
    resolution = cfg["instrument"]["resolution"]
    throughput = cfg["efficiency"]["total"]
    zp = cfg["photometry"]["zero_point_erg_per_cm2_s_a"]

    delta_lambda_a = wave0_a / resolution
    photon_energy_erg = _H_ERG_S * _C_CM_S / (wave0_a * 1e-8)  # λ in cm

    flux_erg_s_a = zp * area_cm2 * 10.0 ** (-mag / 2.5)
    signal_erg   = flux_erg_s_a * delta_lambda_a * exptime_s * throughput
    return signal_erg / photon_energy_erg


def compute_snr(
    mag: np.ndarray,
    exptime_s: float | np.ndarray,
    n_sub: int,
    cfg: dict,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return (SNR, N_phot, CIC_var, dark_var) arrays."""
    mag      = np.asarray(mag, dtype=float)
    exptime_s = np.asarray(exptime_s, dtype=float)

    n_phot_total = photons_per_resel(mag, exptime_s, cfg)

    spatial_pix = cfg["detector"]["spatial_extent_pix"]
    cic  = cfg["detector"]["clock_induced_charges_e_per_pix"]
    dark = cfg["detector"]["dark_current_e_per_s_per_pix"]

    cic_var  = cic  * spatial_pix * n_sub
    dark_var = dark * spatial_pix * exptime_s
    variance = n_phot_total + cic_var + dark_var

    snr = np.where(variance > 0, n_phot_total / np.sqrt(variance), 0.0)
    return snr, n_phot_total, np.broadcast_to(cic_var, snr.shape), dark_var


def _to_list(arr) -> list:
    return np.where(np.isfinite(arr), arr, None).tolist()


@app.route("/")
def index():
    cfg = load_config()
    # Pass config as JSON to the template so JS can use it directly
    return render_template("index.html", config_json=json.dumps(cfg))


@app.route("/compute", methods=["POST"])
def compute():
    """Return SNR curves and noise budget as JSON."""
    payload = request.get_json(force=True)
    cfg = load_config()

    # Allow per-request override of the four user-editable parameters
    if "efficiency" in payload:
        cfg["efficiency"]["total"] = float(payload["efficiency"])
    if "spatial_pix" in payload:
        cfg["detector"]["spatial_extent_pix"] = int(payload["spatial_pix"])
    if "dark" in payload:
        cfg["detector"]["dark_current_e_per_s_per_pix"] = float(payload["dark"])
    if "cic" in payload:
        cfg["detector"]["clock_induced_charges_e_per_pix"] = float(payload["cic"])
    if "resolution" in payload:
        cfg["instrument"]["resolution"] = int(payload["resolution"])

    exptime_s   = float(payload.get("exptime_s", cfg["defaults"]["exposure_time_s"]))
    frame_rate  = float(payload.get("frame_rate_hz", cfg["defaults"]["frame_rate_hz"]))
    n_sub       = max(1, round(exptime_s * frame_rate))
    target_mag  = float(payload.get("target_mag", cfg["defaults"]["target_magnitude"]))

    # ── SNR vs magnitude ──────────────────────────────────────────────────────
    mag_grid = np.linspace(
        cfg["photometry"]["mag_min"],
        cfg["photometry"]["mag_max"],
        300,
    )
    snr_mag, n_phot_mag, _, _ = compute_snr(mag_grid, exptime_s, n_sub, cfg)

    # ── SNR vs exposure time at target magnitude ───────────────────────────────
    time_grid = np.logspace(1, math.log10(3 * 3600), 300)   # 10 s … 3 h
    snr_time, _, _, _ = compute_snr(
        np.full_like(time_grid, target_mag), time_grid, n_sub, cfg
    )

    # ── Noise budget at (target_mag, exptime_s) ───────────────────────────────
    snr_pt, n_phot_pt, cic_var_pt, dark_var_pt = compute_snr(
        np.array([target_mag]), exptime_s, n_sub, cfg
    )
    n_phot_pt   = float(n_phot_pt[0])
    cic_var_pt  = float(np.asarray(cic_var_pt).flat[0])
    dark_var_pt = float(np.asarray(dark_var_pt).flat[0])
    total_var   = n_phot_pt + cic_var_pt + dark_var_pt

    noise_budget = {
        "n_phot":     round(n_phot_pt, 2),
        "shot_frac":  round(n_phot_pt   / total_var * 100, 1) if total_var else 0,
        "cic_frac":   round(cic_var_pt  / total_var * 100, 1) if total_var else 0,
        "dark_frac":  round(dark_var_pt / total_var * 100, 1) if total_var else 0,
        "snr":        round(float(snr_pt[0]), 2),
    }

    return jsonify(
        mag_grid=_to_list(mag_grid),
        snr_mag=_to_list(snr_mag),
        n_phot_mag=_to_list(n_phot_mag),
        time_grid=_to_list(time_grid),
        snr_time=_to_list(snr_time),
        noise_budget=noise_budget,
        n_sub=n_sub,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5050)
