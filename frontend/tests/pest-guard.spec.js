const { test, expect } = require('@playwright/test');
const path = require('path');

const tinyPng = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlMZQAAAABJRU5ErkJggg==', 'base64');

const result = {
  ok: true,
  analysis_id: 'test-analysis-id',
  created_at: new Date().toISOString(),
  status: 'uncertain',
  development_mode: true,
  farmer_message: 'The condition could not be identified reliably.',
  detected_crop: 'tomato', plant_part: 'leaf', growth_stage: 'fruiting', harvest_stage: 'pre_harvest',
  diseases: [], pests: [], possible_alternatives: [],
  severity: { level: 'unknown', affected_percentage: null },
  images: [{ image_id: 'image-1', original_name: 'plant.jpg', quality: { suitable: true }, urls: { original: '/api/vision/file/test-analysis-id/original.jpg', annotated: null, zoom: null } }],
  recommendations: { selected: [{ type: 'natural', title: 'Collect more views', detail: 'Photograph both sides of the affected leaf.', cost_category: 'low' }], weather_warnings: [], commercial_warning: 'No verified chemical record is configured.' },
  model_summary: { models: {} },
  voice_summary: 'The condition could not be identified reliably.',
  disclaimer: 'Advisory only.',
};

async function mockApis(page) {
  await page.addInitScript(() => {
    localStorage.setItem('agri_auth_token', 'test-token');
    localStorage.setItem('agri_auth_user', JSON.stringify({ id: 1, name: 'Test Farmer', phone: '9999999999' }));
  });
  await page.route('**/api/auth/me', (route) => route.fulfill({ json: { id: 1, name: 'Test Farmer', phone: '9999999999' } }));
  await page.route('**/api/vision/health', (route) => route.fulfill({ json: { ok: true, development_mode: true, status: 'development_mode' } }));
  await page.route('**/api/vision/history**', (route) => route.fulfill({ json: { ok: true, items: [] } }));
  await page.route('**/api/vision/analyze-session', (route) => route.fulfill({ json: result }));
  await page.route('**/api/vision/file/**', (route) => route.fulfill({ body: tinyPng, contentType: 'image/png' }));
}

test('upload flow renders an uncertainty-safe result', async ({ page }) => {
  await mockApis(page);
  await page.goto('/pest-guard');
  await page.locator('input[type="file"][multiple]').setInputFiles(path.join(__dirname, 'fixtures', 'plant.jpg'));
  await expect(page.getByText('plant.jpg')).toBeVisible();
  await page.getByRole('button', { name: /Analyze images/i }).click();
  await expect(page.getByText('The condition could not be identified reliably.')).toBeVisible();
  await expect(page.getByText('No verified chemical record is configured.')).toBeVisible();
});

test('scanner remains usable on a mobile viewport', async ({ page }) => {
  await mockApis(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/pest-guard');
  await expect(page.getByRole('button', { name: /Take photo/i })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2);
  expect(overflow).toBeFalsy();
});
