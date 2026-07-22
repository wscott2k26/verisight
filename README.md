# VeriSight 2.2

VeriSight is a full-stack media-forensics application that screens photos and videos for signals associated with AI generation, deepfakes, filters, retouching and digital manipulation.

It combines an optional local Hugging Face classifier with transparent, file-dependent forensic checks. When the neural model cannot load, the interface clearly labels the result as a lower-confidence forensic fallback instead of returning a canned score.

## Deploy the complete app

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/wscott2k26/verisight)

The Render Blueprint creates one full-stack service. The premium Vite website and FastAPI detector share the same HTTPS address, so there is no frontend/backend URL wiring or production CORS setup.

### Hosting requirement

The included neural classifier uses PyTorch and needs more memory than a 512 MB free instance can reliably provide. `render.yaml` therefore requests a paid 2 GB Standard service and a 5 GB persistent model cache. Render displays the price and complete resource plan before you approve the deployment.

After approval:

- Render builds the premium frontend.
- Render builds the CPU-only detector container.
- The app receives an HTTPS `onrender.com` address.
- The model downloads on the first neural scan and stays in the persistent cache.
- Future commits deploy automatically only after GitHub checks pass.

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
- Single-origin production container
- Render Blueprint with health checks and persistent model cache
- Optional Vercel configuration for a separately hosted frontend
- GitHub Actions frontend, backend and production-container verification

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

This skips Transformers/PyTorch while retaining the real file-dependent forensic engine:

```cmd
pip install -r backend\requirements-lite.txt
set ENABLE_ML=false
npm run dev:all
```

## Optional separate Vercel frontend

The recommended production setup is the single Render service above. A separate Vercel frontend remains supported:

1. Import this repository into Vercel.
2. Set `VITE_API_URL` to the deployed API origin without a trailing slash.
3. Use `npm run build` and output directory `dist`.
4. Add the Vercel origin to `CORS_ORIGINS` on the API service.

## Important limitations

- Scores are probabilistic screening, not proof.
- Video analysis samples representative visual frames and does not inspect synthetic audio.
- Screenshots, social-media compression, filters and new generators can cause false positives and false negatives.
- Do not advertise a universal accuracy percentage without validation against a representative labeled dataset.
- Never use one score as the sole basis for accusing a person or making legal, employment, school, financial or safety decisions.

## Privacy behavior

Images are analyzed from request memory. Videos are written to a randomly named temporary file because video decoding requires seekable input; the file is deleted after success or failure. The application does not intentionally maintain a permanent server-side media library. Recent scan summaries are stored only in the current browser.
