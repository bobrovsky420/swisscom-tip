// Serve the built UI locally first. Every API request is mocked; no real job,
// model request or human review is created by this check.
import { chromium, expect } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const folder = new URL('../../.local/admin/v3-extraction-smoke/', import.meta.url);
await mkdir(folder, { recursive: true });
const v3 = 'concept_extraction_v3';
const v4 = 'concept_extraction_v4';
const candidate = {
  candidate_id: 'v3-fixture-candidate', preferred_label: 'Residence fixture',
  description: 'Synthetic concept for testing the V3 review display.',
  scope: 'EU/EFTA nationals covered by this synthetic source section.',
  user_questions: ['Which residence procedure does this source describe?', 'Who does the source apply to?'],
  evidence: [{ section_id: 'section-1', quote: 'Synthetic source evidence for the V3 concept.' }],
};
const v4Candidate = {
  candidate_id: 'v4-fixture-candidate', preferred_label: 'Historical structured fixture',
  description: 'Synthetic historical V4 result.',
  structured_claims: [{ claim_id: 'claim-1', statement: 'A retained structured statement.', conditions: [{ text: 'A retained structured condition.' }] }],
  evidence: [{ section_id: 'block-1', quote: 'Synthetic source evidence for the historical V4 claim.' }],
};
const common = {
  status: 'completed', request: {}, log: 'Synthetic completed job.',
  result_sha256: 'a'.repeat(64), error: null, cancel_requested: false,
  created_at: '2026-09-10T18:00:00Z', started_at: '2026-09-10T18:00:00Z', finished_at: '2026-09-10T18:01:00Z',
};
const jobs = [
  { ...common, job_id: 'v3-plan', kind: 'plan', result: {
    prompt_profile: v3, planned_request_ceiling: 8, model_requests_sent: 0,
    pages: [{ source: 'C:\\fixtures\\residence.html', planned_request_ceiling: 8, source_inventory: [] }],
  } },
  { ...common, job_id: 'v3-result', kind: 'extract', result: { reports: [{ prompt_profile: v3, candidates: [candidate] }] } },
  { ...common, job_id: 'v4-plan', kind: 'plan', result: {
    prompt_profile: v4, planned_request_ceiling: 12, model_requests_sent: 0,
    pages: [{ source: 'C:\\fixtures\\historic.html', planned_request_ceiling: 12, source_inventory: [
      { section_id: 'block-1', status: 'pending', reason: '', evidence_text: 'Historical eligible source block.' },
      { section_id: 'block-2', status: 'excluded_policy', reason: 'navigation', evidence_text: 'Historical excluded navigation.' },
    ] }],
  } },
  { ...common, job_id: 'v4-result', kind: 'extract', result: { reports: [{ prompt_profile: v4, candidates: [v4Candidate] }] } },
];
const asset = {
  asset_id: 'fixture-asset', source_id: 'zh-eu-efta', filename: 'residence.html', sha256: 'b'.repeat(64),
  origin: 'Synthetic fixture', size: 1500, created_at: common.created_at,
};
const catalog = {
  extraction_profile: v3, sources: [], crawl_profiles: ['smoke'], max_pages: 10, max_requests: 30,
  profiles: [{ name: 'deepseek_v4_1_flash', adapter: 'deepseek', model: 'deepseek-flash', credential_ready: true, selected: true }],
};
const browser = await chromium.launch({ channel: process.platform === 'win32' ? 'msedge' : undefined, headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
const unexpectedRequests = [];
const planRequests = [];
page.on('pageerror', error => errors.push(error.message));
await page.route('**/api/**', async route => {
  const request = route.request();
  const path = new URL(request.url()).pathname;
  const method = request.method();
  const respond = json => route.fulfill({ status: 200, json });
  if (method === 'GET') {
    if (path === '/api/catalog') return respond(catalog);
    if (path === '/api/assets') return respond([asset]);
    if (path === `/api/assets/${asset.asset_id}/preview`) return respond({
      title: 'V3 parsed source fixture', language: 'en', extraction_profile: v3,
      sections: [{ section_id: 'section-1', text: 'Visible V3 source text after filtering.' }],
      characters: 45, excluded_sections: 3,
    });
    if (path === '/api/releases' || path.endsWith('/reviews')) return respond([]);
    if (path === '/api/jobs') return respond(jobs);
    const job = jobs.find(item => path === `/api/jobs/${item.job_id}`);
    if (job) return respond(job);
  }
  if (method === 'POST' && path === '/api/jobs' && request.postDataJSON().kind === 'plan') {
    planRequests.push(request.postDataJSON());
    return respond(jobs[0]);
  }
  unexpectedRequests.push(`${method} ${path}`);
  return route.abort('blockedbyclient');
});

try {
  await page.goto('http://127.0.0.1:8000');
  await page.getByRole('button', { name: 'Saved pages', exact: true }).click();
  await expect(page.getByText('V3 concepts and evidence. Model outputs remain experimental.', { exact: true })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Extraction model', exact: true })).toHaveValue('deepseek_v4_1_flash');
  await page.getByRole('button', { name: 'Inspect parsed text', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('heading', { name: 'V3 parsed source fixture', exact: true })).toBeVisible();
  await expect(dialog.getByText('Visible V3 source text after filtering.', { exact: true })).toBeVisible();
  await expect(dialog.getByText('V3 concepts and evidence. 3 sections excluded by the extraction profile.', { exact: true })).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('checkbox', { name: 'Select page zh-eu-efta', exact: true }).check();
  await page.getByRole('button', { name: 'Run extraction', exact: true }).click();
  await expect(dialog.getByText('deepseek-flash using V3 concepts and evidence', { exact: false })).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Preview extraction plan', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Extraction plan', exact: true })).toBeVisible();
  await expect(page.getByText('V3 concepts and evidence', { exact: true })).toBeVisible();
  await expect(page.getByText('Page 1: 8 planned model requests', { exact: true })).toBeVisible();
  await expect(page.getByText('residence.html', { exact: true })).toBeVisible();
  await expect(page.getByText('Model requests sent: 0.', { exact: false })).toBeVisible();
  await expect(page.getByText('0 content blocks', { exact: false })).toHaveCount(0);
  expect(planRequests).toEqual([{ kind: 'plan', asset_ids: [asset.asset_id], source_ids: [], profile: 'deepseek_v4_1_flash' }]);
  await page.screenshot({ path: fileURLToPath(new URL('v3-plan.png', folder)), animations: 'disabled' });

  await page.locator('.job-item').nth(1).click();
  const card = page.locator('.candidate');
  await expect(card.getByRole('heading', { name: candidate.preferred_label, exact: true })).toBeVisible();
  await expect(card.getByText('Concept scope', { exact: true })).toBeVisible();
  await expect(card.getByText(candidate.scope, { exact: true })).toBeVisible();
  for (const question of candidate.user_questions) await expect(card.getByText(question, { exact: true })).toBeVisible();
  await expect(card.getByText(candidate.evidence[0].quote, { exact: false })).toBeVisible();
  await expect(card.getByText('Proposed claims', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Inspect full report', { exact: true })).toBeVisible();
  await card.getByRole('button', { name: 'needs changes', exact: true }).click();
  await expect(dialog.getByLabel('Review comment')).toBeFocused();
  await dialog.getByLabel('Review comment').fill('A cancelled synthetic review comment.');
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await card.getByRole('button', { name: 'reject', exact: true }).click();
  await expect(dialog.getByLabel('Review comment')).toHaveValue('');
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await page.screenshot({ path: fileURLToPath(new URL('v3-candidate.png', folder)), animations: 'disabled' });

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(card.getByText(candidate.scope, { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.locator('.job-item').nth(2).click();
  await expect(page.getByText('V4 structured claims', { exact: true })).toBeVisible();
  await expect(page.getByText('Page 1: 1 content blocks', { exact: true })).toBeVisible();
  await expect(page.getByText('Historical eligible source block.', { exact: true })).toBeVisible();
  await expect(page.getByText('Historical excluded navigation.', { exact: true })).toHaveCount(0);
  await page.locator('.job-item').nth(3).click();
  await expect(card.getByText('Proposed claims', { exact: true })).toBeVisible();
  await expect(card.getByText(v4Candidate.structured_claims[0].statement, { exact: true })).toBeVisible();
  await expect(card.getByText(v4Candidate.structured_claims[0].conditions[0].text, { exact: true })).toBeVisible();
  await expect(card.getByText('Concept scope', { exact: true })).toHaveCount(0);
  expect(errors).toEqual([]);
  expect(unexpectedRequests).toEqual([]);
  const report = {
    passed: true, api: 'all requests mocked', real_job_writes: 0, real_review_writes: 0, model_calls: 0,
    checks: ['V3 profile and DeepSeek V4.1 Flash model displayed separately', 'V3 filtered source preview',
      'extraction confirmation names profile and model', 'V3 page/request plan without misleading empty inventory',
      'V3 scope, questions and source evidence', 'fresh review comments on V3 cards', 'V3 mobile layout',
      'historical V4 plan inventory', 'historical V4 claims and conditions', 'no browser exceptions'],
  };
  await writeFile(new URL('report.json', folder), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}
