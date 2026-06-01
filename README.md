# VROOMM ETC

Exposure Time Calculator for the **VROOMM** high-resolution spectrograph at the **OMM 1.6-m** telescope.

## Quick start

```bash
pip install -r requirements.txt
python serve.py          # → http://127.0.0.1:5050
```

Open http://127.0.0.1:5050 in your browser.

## Files

| File | Purpose |
|------|---------|
| `config.yaml` | All default instrument/detector parameters |
| `app.py` | Flask backend — physics engine + `/compute` API |
| `serve.py` | Waitress WSGI launcher (no tty issues) |
| `templates/index.html` | Single-page UI (Bootstrap 5 + Plotly.js) |

## Inputs

- **t_exp** — single exposure time (10 s – 3 h)
- **Sub-exposures** — number of readouts (total time = t_exp)
- **r mag** — SDSS r target magnitude (8–20)
- **Target SNR** — used for limiting-magnitude and required-time computations
- **Advanced**: efficiency, spatial pixels, dark current, CIC

## Physics

Signal photons per resolution element:

```
N = ZP × Area × 10^(−mag/2.5) × η × (λ₀/R) × t_exp
```

Noise variance:

```
σ² = N  +  CIC × spatial_pix × n_sub  +  dark × spatial_pix × t_exp
```

SNR = N / σ

## Default instrument parameters

See `config.yaml`. Key values:

| Parameter | Value |
|-----------|-------|
| Telescope | OMM 1.6-m (D = 160 cm) |
| λ₀ | 6204.29 Å |
| Resolution | 120 000 |
| Pixel sampling | 1 km/s |
| Efficiency | 10% |
| Spatial extent | 8 pix |
| Dark current | 1.6×10⁻⁴ e⁻/s/pix |
| CIC | 0.001 e⁻/pix/readout |
