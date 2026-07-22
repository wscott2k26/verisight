# VeriSight 2.1

VeriSight is a full-stack media-forensics application that screens photos and videos for signals associated with AI generation, deepfakes, filters, retouching and digital manipulation.

It uses an optional local Hugging Face image classifier plus transparent file-dependent forensic checks. If the neural model cannot load, the interface clearly labels the scan as a lower-confidence forensic fallback instead of returning a canned score.

## Included

- Premium responsive cyber-forensics dashboard
- Photo and AI/deepfake-video upload modes
- Real file-dependent image analysis
- Adaptive video frame sampling and peak timestamp
- Evidence heatmaps and sampled-frame thumbnails
- Plain-language explanations and responsible next steps
- Downloadable PNG report card and JSON report
- Browser-only scan history
- Temporary video cleanup and `no-store` API responses
- Render backend and Vercel frontend configuration
- GitHub Actions frontend/backend smoke verification

## Local Windows start

```cmd
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r backend\requirements.txt
npm install
npm run dev:all
```

Open `http://localhost:5173`.

The API documentation is at `http://127.0.0.1:8000/docs`.

### Faster forensic-only installation

This skips the optional Transformers/PyTorch model while retaining the real forensic engine:

```cmd
pip install -r backend\requirements-lite.txt
set ENABLE_ML=false
npm run dev:all
```

## Deploy

### Backend — Render

1. Create a Render Blueprint from this repository using `render.yaml`.
2. Set `CORS_ORIGINS` to the final frontend origin.
3. The first neural scan may need several minutes to download and cache the model.

### Frontend — Vercel

1. Import this repository into Vercel.
2. Set `VITE_API_URL` to the deployed backend origin, without a trailing slash.
3. Build command: `npm run build`; output directory: `dist`.

## Important limitations

- Scores are probabilistic screening, not proof.
- Video analysis samples representative frames and does not inspect synthetic audio.
- Screenshots, social-media compression, filters and new AI generators can cause false positives and false negatives.
- Do not advertise a universal accuracy percentage without validation against a representative labeled dataset.
- Never use one score as the sole basis for accusing a person or making legal, employment, school, financial or safety decisions.

## Privacy behavior

Images are analyzed from request memory. Videos are written to a randomly named temporary file because video decoding requires seekable input; the file is deleted after success or failure. The included application does not intentionally maintain a permanent server-side media library. Recent scan summaries are stored only in the current browser.
