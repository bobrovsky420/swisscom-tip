// Serve the built UI locally first. Every API request is mocked; no real review,
// job, crawler or model request is created by this check.
import { chromium, expect } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const folder = new URL('../../.local/admin/review-dialog-smoke/', import.meta.url);
await mkdir(folder, { recursive: true });
const resultHash = 'a'.repeat(64);
const candidates = Array.from({ length: 8 }, (_, index) => ({
  candidate_id: `mock-candidate-${index + 1}`,
  preferred_label: `Review fixture ${index + 1}`,
  description: 'A synthetic candidate used to check review actions on a long result page.',
  structured_claims: Array.from({ length: 4 }, (_, claim) => ({
    claim_id: `mock-claim-${index + 1}-${claim + 1}`,
    statement: `Synthetic claim ${claim + 1}: compare the proposed statement with its source evidence.`,
    conditions: [{ text: 'This example exists only in the intercepted browser response.' }],
  })),
  evidence: [{ section_id: `section-${index + 1}`, quote: 'Synthetic source excerpt. No real extracted candidate or review is modified.' }],
}));
const job = {
  job_id: 'mock-review-dialog-job', kind: 'extract', status: 'completed', request: {},
  log: 'Mock extraction completed.', result: { reports: [{ title: 'Review dialog fixture', candidates }] },
  result_sha256: resultHash, error: null, cancel_requested: false,
  created_at: '2026-09-10T08:25:00Z', started_at: '2026-09-10T08:25:00Z', finished_at: '2026-09-10T08:26:00Z',
};
const catalog = { sources: [], profiles: [], crawl_profiles: [], max_pages: 10, max_requests: 30 };
const browser = await chromium.launch({ channel: process.platform === 'win32' ? 'msedge' : undefined, headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
const unexpectedRequests = [];
const submissions = [];
const reviews = [];
let failNextReview = false;
let releaseSave;
let pendingSave;
page.on('pageerror', error => errors.push(error.message));
await page.route('**/api/**', async route => {
  const request = route.request();
  const path = new URL(request.url()).pathname;
  const method = request.method();
  const respond = (json, status = 200) => route.fulfill({ status, json });
  if (method === 'GET') {
    if (path === '/api/catalog') return respond(catalog);
    if (path === '/api/assets' || path === '/api/releases') return respond([]);
    if (path === '/api/jobs') return respond([job]);
    if (path === `/api/jobs/${job.job_id}`) return respond(job);
    if (path === `/api/jobs/${job.job_id}/reviews`) return respond(reviews);
  }
  if (method === 'POST' && path === `/api/jobs/${job.job_id}/reviews`) {
    const body = request.postDataJSON();
    submissions.push(body);
    if (pendingSave) await pendingSave;
    if (failNextReview) {
      failNextReview = false;
      return respond({ detail: 'Simulated save failure. Try again.' }, 503);
    }
    reviews.push({ ...body, created_at: '2026-09-10T09:00:00Z' });
    return respond({ message: 'Draft review recorded.' });
  }
  unexpectedRequests.push(`${method} ${path}`);
  return route.abort('blockedbyclient');
});

const card = index => page.locator('.candidate').filter({ has: page.getByRole('heading', { name: candidates[index].preferred_label, exact: true }) });
const dialog = page.getByRole('dialog');
const comment = () => dialog.getByLabel('Review comment');
const save = () => dialog.getByRole('button', { name: 'Save review', exact: true });
const assertSubmission = (index, candidateIndex, decision, notes) => {
  expect(submissions[index]).toEqual({
    candidate_id: candidates[candidateIndex].candidate_id,
    decision, reviewer: 'GUI reviewer', notes, result_sha256: resultHash,
  });
};
async function openReview(index, decision, title) {
  await card(index).getByRole('button', { name: decision, exact: true }).click();
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('heading', { name: title, exact: true })).toBeVisible();
  await expect(dialog.getByText(candidates[index].preferred_label, { exact: true })).toBeVisible();
  await expect(comment()).toHaveValue('');
  await expect(comment()).toBeFocused();
  await expect(save()).toBeDisabled();
}
async function expectReturnedToAction(index, decision, previousScroll) {
  await expect(card(index).getByRole('button', { name: decision, exact: true })).toBeFocused();
  const currentScroll = await page.evaluate(() => window.scrollY);
  expect(Math.abs(currentScroll - previousScroll)).toBeLessThan(80);
}

try {
  await page.goto('http://127.0.0.1:8000');
  await page.getByRole('button', { name: 'Builds & review', exact: true }).click();
  await page.locator('.job-item').click();
  await expect(page.getByRole('heading', { name: 'Candidate review', exact: true })).toBeVisible();

  // No reviewer has been entered at the top. A bottom-card action must still
  // let the reviewer supply everything needed without returning to that form.
  await card(7).getByRole('button', { name: 'needs changes', exact: true }).scrollIntoViewIfNeeded();
  const scrollBefore = await page.evaluate(() => window.scrollY);
  expect(scrollBefore).toBeGreaterThan(1000);
  await openReview(7, 'needs changes', 'Needs changes');
  expect(await page.evaluate(() => window.scrollY)).toBe(scrollBefore);
  await comment().fill('This cancelled comment must not be reused.');
  await expect(save()).toBeDisabled();
  await dialog.getByLabel('Reviewer name').fill('GUI reviewer');
  await expect(save()).toBeEnabled();
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expectReturnedToAction(7, 'needs changes', scrollBefore);
  expect(submissions).toHaveLength(0);

  await openReview(7, 'needs changes', 'Needs changes');
  await expect(dialog.getByLabel('Reviewer name')).toHaveValue('GUI reviewer');
  await comment().fill('   ');
  await expect(save()).toBeDisabled();
  await comment().fill('Keep the missing source condition.');
  await page.screenshot({ path: fileURLToPath(new URL('desktop-dialog.png', folder)), animations: 'disabled' });
  pendingSave = new Promise(resolve => { releaseSave = resolve; });
  await save().click();
  await expect.poll(() => submissions.length).toBe(1);
  await expect(comment()).toBeDisabled();
  await expect(dialog.getByLabel('Reviewer name')).toBeDisabled();
  await expect(dialog.getByRole('button', { name: 'Cancel', exact: true })).toBeDisabled();
  await page.keyboard.press('Escape');
  await expect(dialog).toBeVisible();
  await page.mouse.click(5, 5);
  await expect(dialog).toBeVisible();
  expect(submissions).toHaveLength(1);
  releaseSave();
  pendingSave = undefined;
  await expect(dialog).not.toBeVisible();
  await expectReturnedToAction(7, 'needs changes', scrollBefore);
  assertSubmission(0, 7, 'needs_changes', 'Keep the missing source condition.');
  await expect(card(7).getByText('Draft review recorded.', { exact: true })).toBeVisible();

  // A second decision on the same candidate also starts with an empty comment.
  await openReview(7, 'reject', 'Reject draft');
  await comment().fill('The source does not support this draft.');
  await save().click();
  await expect(dialog).not.toBeVisible();
  expect(submissions).toHaveLength(2);
  assertSubmission(1, 7, 'reject', 'The source does not support this draft.');

  // Failure must remain beside the editable note. Retrying keeps the candidate,
  // decision, reviewer and exact result revision bound to that submission.
  await openReview(6, 'needs changes', 'Needs changes');
  await comment().fill('Separate the alternative requirements.');
  failNextReview = true;
  await save().click();
  await expect(dialog.getByText('Simulated save failure. Try again.', { exact: true })).toBeVisible();
  await expect(comment()).toHaveValue('Separate the alternative requirements.');
  await expect(comment()).toBeEnabled();
  await expect(save()).toBeEnabled();
  expect(submissions).toHaveLength(3);
  await save().click();
  await expect(dialog).not.toBeVisible();
  expect(submissions).toHaveLength(4);
  assertSubmission(2, 6, 'needs_changes', 'Separate the alternative requirements.');
  assertSubmission(3, 6, 'needs_changes', 'Separate the alternative requirements.');

  // Direct acceptance keeps its own optional note, never a previous dialog note.
  await card(5).getByRole('button', { name: 'accept draft', exact: true }).click();
  await expect.poll(() => submissions.length).toBe(5);
  assertSubmission(4, 5, 'accept_draft', '');
  await expect(card(5).getByText('Draft review recorded.', { exact: true })).toBeVisible();
  await page.getByLabel(/acceptance note/i).fill('Source comparison complete.');
  await card(4).getByRole('button', { name: 'accept draft', exact: true }).click();
  await expect.poll(() => submissions.length).toBe(6);
  assertSubmission(5, 4, 'accept_draft', 'Source comparison complete.');
  await expect(card(4).getByText('Draft review recorded.', { exact: true })).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  await openReview(7, 'reject', 'Reject draft');
  await comment().fill('A fresh mobile comment.');
  const bounds = await dialog.boundingBox();
  expect(bounds.x).toBeGreaterThanOrEqual(0);
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(390);
  expect(bounds.y).toBeGreaterThanOrEqual(0);
  expect(bounds.y + bounds.height).toBeLessThanOrEqual(844);
  await expect(save()).toBeInViewport();
  await page.screenshot({ path: fileURLToPath(new URL('mobile-dialog.png', folder)), animations: 'disabled' });
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await openReview(7, 'reject', 'Reject draft');
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  expect(submissions).toHaveLength(6);
  expect(reviews).toHaveLength(5);
  expect(unexpectedRequests).toEqual([]);
  expect(errors).toEqual([]);
  const report = {
    passed: true, api: 'all requests mocked', real_review_writes: 0, model_calls: 0,
    checks: ['long-page actions', 'focus and scroll restoration after save/cancel', 'comment autofocus', 'reviewer entry in dialog', 'fresh comment on every open',
      'required reviewer and comment', 'cancel without submission', 'candidate/decision/result binding',
      'pending save locks dismissal', 'inline failure and retry', 'candidate-local success',
      'separate acceptance notes', 'mobile dialog fit', 'no browser exceptions'],
  };
  await writeFile(new URL('report.json', folder), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report, null, 2));
} finally {
  releaseSave?.();
  await browser.close();
}
