# AgriSarthi Next.js frontend

```bash
cp .env.local.example .env.local
npm ci
npm run dev
```

Open `http://127.0.0.1:3000`. The AI Crop Pest and Disease Vision Analyzer is at `/pest-guard` and uses the existing Next.js `/api` rewrite to reach FastAPI.

Production build:

```bash
npm run build
npm start
```

Optional Playwright checks:

```bash
npm install --save-dev @playwright/test
npx playwright install chromium
npm run test:e2e
```

The scanner supports camera/gallery/drag-and-drop input, multiple views, farmer context, simple/advanced results, regional-language voice explanation, history, detailed expert-review feedback, a farmer-friendly HTML report and technical JSON export. When backend weights are absent, it displays development mode and never renders a fabricated diagnosis.
