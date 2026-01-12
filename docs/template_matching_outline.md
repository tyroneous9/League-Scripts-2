Template matching outline

Overview

This document describes the planned coarse→fine normalized-grayscale correlation template matching pipeline.

1) Precompute templates
- For each UI resolution (keyed by "{width}x{height}"), store preprocessed template images in `templates/{width}x{height}/`.
- Preprocessing for now: convert to grayscale, apply Gaussian blur (small kernel). Write files using the naming convention:
  `{name}_{width}x{height}_preproc.png`
- Maintain a single `templates/index.json` mapping resolution -> list of template entries. Minimal entry fields: `id`, `name`, `path`.

2) Runtime loader
- Load `templates/index.json` at startup and pick entries for the current runtime resolution (e.g., "1920x1080").
- Strict mode: fail fast if resolution not present. Optional: fallback to "default" or closest key if enabled.

3) Matching algorithm (coarse→fine)
- Downscale the target frame to a coarse search size (e.g., reduce both dimensions by factor 2 or to a target max width such as 960px). Downscaling the frame is faster because it reduces convolution cost.
- For each template:
  - Use the preprocessed template (grayscale+blur) loaded into memory.
  - If coarse scale differs from template scale, downscale template similarly to match the scaled frame.
  - Run `cv2.matchTemplate(coarse_frame_gray, coarse_template, cv2.TM_CCOEFF_NORMED)`.
  - Collect candidate locations above a loose threshold (e.g., 0.6).
- For each candidate: compute an ROI in the original full-resolution frame, load the full-resolution preprocessed template, and re-run `matchTemplate` on the ROI for a tighter score.
- Return top-K matches per template (sorted by score), along with bounding boxes and scores.

Notes
- Use grayscale+blur for templates and frame preproc for speed/stability.
- Avoid writing files at runtime; load precomputed variants into memory at startup.
- Exact-match policy: current implementation will require an exact resolution key to be present in `index.json`.

Benchmarks and tuning
- Measure `matchTemplate` cost vs template area; tune coarse factor to minimize full-res refinements.
- Tune blur kernel sizes to balance aliasing vs precision.
