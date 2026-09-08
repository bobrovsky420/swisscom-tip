// Real local API/worker/database. No crawler or model request is started.
import { chromium, expect } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';

const folder = new URL('../../.local/admin/', import.meta.url);
await mkdir(folder, { recursive: true });
const browser = await chromium.launch({ channel: process.platform === 'win32' ? 'msedge' : undefined, headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on('pageerror', error => errors.push(error.message));
try {
  await page.goto('http://127.0.0.1:8000');
  await expect(page.getByRole('heading', { name: 'Start with the source.' })).toBeVisible();
  await expect(page.getByRole('checkbox', { name: 'Select ch-sem-residence-en', exact: true })).toBeChecked();
  await page.screenshot({ path: new URL('sources.png', folder).pathname.replace(/^\/(\w:)/, '$1'), fullPage: false });
  await page.getByRole('button', { name: 'Load saved pilot pages' }).click();
  await expect(page.getByRole('heading', { name: 'See what the parser sees.' })).toBeVisible();
  await expect(page.getByRole('checkbox', { name: 'Select page ch-sem-residence-en', exact: true })).toBeChecked();
  const card = page.locator('.page-card').filter({ has: page.getByRole('heading', { name: 'ch-sem-residence-en', exact: true }) });
  await card.getByRole('button', { name: 'Inspect parsed text' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByText('Anyone who works', { exact: false })).toBeVisible();
  await page.screenshot({ path: new URL('preview.png', folder).pathname.replace(/^\/(\w:)/, '$1') });
  await page.keyboard.press('Escape');
  // Use one saved page for a small, deterministic offline CLI plan.
  for (const id of ['ch-sem-residence-de', 'zh-eu-efta']) await page.getByRole('checkbox', { name: `Select page ${id}`, exact: true }).uncheck();
  await page.getByRole('button', { name: 'Preview extraction plan', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Extraction plan', exact: true })).toBeVisible();
  await expect(page.getByText('Model requests sent: 0.', { exact: false })).toBeVisible({ timeout: 30000 });
  await page.screenshot({ path: new URL('build.png', folder).pathname.replace(/^\/(\w:)/, '$1'), fullPage: false });
  await page.getByRole('button', { name: 'Stored knowledge', exact: true }).click();
  await expect(page.getByText('zh-e002', { exact: true })).toBeVisible();
  await page.screenshot({ path: new URL('corpus.png', folder).pathname.replace(/^\/(\w:)/, '$1'), fullPage: false });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('heading', { name: 'Explore your evidence.' })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflow).toBe(false);
  expect(errors).toEqual([]);
  const report = { passed: true, browser: 'Chromium', api: 'real local Control API', database: 'real PostgreSQL',
    checks: ['default sources', 'archived page loading', 'filtered preview', 'offline CLI plan and polling', 'stored evidence', 'mobile layout', 'no browser exceptions'], model_calls: 0, crawl_calls: 0 };
  await writeFile(new URL('browser-smoke.json', folder), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}
