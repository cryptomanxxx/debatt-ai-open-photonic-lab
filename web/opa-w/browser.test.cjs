const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const { resolve } = require('node:path');
const { after, before, test } = require('node:test');
const { chromium } = require('playwright');

const origin = 'http://127.0.0.1:4174';
let server;
let browser;

before(async () => {
  server = spawn('python3', ['-u', '-m', 'http.server', '4174', '--bind', '127.0.0.1',
    '--directory', resolve(__dirname, '..')], { stdio: ['ignore', 'pipe', 'ignore'] });
  await Promise.race([
    once(server.stdout, 'data'),
    once(server, 'exit').then(([code]) => { throw new Error('HTTP server exited ' + code); }),
  ]);
  browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH });
});

after(async () => {
  try { await browser?.close(); } finally { server?.kill(); }
});

async function open(chip, width, verify) {
  const page = await browser.newPage({ viewport: { width, height: 960 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto(origin + '/chip' + chip + '/');
    await page.getByRole('heading', { name: new RegExp('Chip ' + chip) }).waitFor();
    await verify(page);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      'Page should fit ' + width + 'px without horizontal scrolling');
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }
}

const action = (page, name) => page.locator('[data-action="' + name + '"]');
const field = (page, name) => page.locator('[name="' + name + '"]');
const reading = (page, name) => page.getByRole('row').filter({
  has: page.getByRole('rowheader', { name, exact: true }),
}).getByRole('cell').innerText();

// Exercise each slider through keyboard input and verify its live numeric label.
async function exerciseSliders(page) {
  for (const slider of await page.locator('input[type="range"]').all()) {
    const name = await slider.getAttribute('name');
    const displayed = page.locator('[data-value="' + name + '"]');
    await slider.press('Home');
    assert.equal(Number(await displayed.innerText()), Number(await slider.getAttribute('min')));
    await slider.press('End');
    assert.equal(Number(await displayed.innerText()), Number(await slider.getAttribute('max')));
  }
}

test('Chip 13 programs a selected 8 × 8 cell, reads both storage modes and preserves state when off', { timeout: 45000 }, () =>
  open(13, 360, async page => {
    await field(page, 'size').selectOption('8');
    assert.equal(await action(page, 'cell').count(), 64);
    await action(page, 'cell').nth(63).click();
    await field(page, 'levels').selectOption('16');
    await field(page, 'target').press('End');
    await action(page, 'write').click();
    assert.equal(await reading(page, 'Programmed phase fraction'), '1.0000');
    await action(page, 'stop').click();
    assert.equal(await reading(page, 'Detector power'), '—');
    await action(page, 'start').click();
    assert.equal(await reading(page, 'Decoded level'), '15');
    await action(page, 'stop').click();
    await field(page, 'size').selectOption('4');
    await field(page, 'size').selectOption('8');
    await action(page, 'cell').nth(63).click();
    assert.equal(await reading(page, 'Programmed phase fraction'), '1.0000');
    await action(page, 'age').click();
    assert.equal(await reading(page, 'Model clock'), '10 units');
    assert.ok(Number(await reading(page, 'Current phase fraction')) < 1);
    await field(page, 'material').selectOption('GSSe');
    await field(page, 'preset').selectOption('multilevel');
    assert.equal(await action(page, 'cell').nth(15).innerText(), '15');
    await field(page, 'preset').selectOption('weak');
    await action(page, 'write').click();
    assert.equal(await reading(page, 'Programmed phase fraction'), '0.0000');
    await action(page, 'stop').click();
    await exerciseSliders(page);
    await action(page, 'reset').click();
    assert.equal(await action(page, 'cell').count(), 16);
  }));

test('Chip 14 computes a signed 4 × 4 product and exposes error and precision', { timeout: 45000 }, () =>
  open(14, 768, async page => {
    assert.equal(await action(page, 'weight').count(), 16);
    assert.deepEqual(await page.getByRole('row').filter({ has: page.getByRole('rowheader', { name: 'y2', exact: true }) })
      .getByRole('cell').allTextContents(), ['-0.5000', '-0.5000', '0.0000']);
    await action(page, 'weight').nth(0).click();
    await field(page, 'weight').press('Home');
    assert.deepEqual(await page.getByRole('row').filter({ has: page.getByRole('rowheader', { name: 'y1', exact: true }) })
      .getByRole('cell').allTextContents(), ['-0.7500', '-0.7500', '0.0000']);
    await field(page, 'preset').selectOption('coarse');
    await field(page, 'bits').selectOption('8');
    await field(page, 'detectorBits').selectOption('12');
    await action(page, 'start').click();
    assert.equal(await page.locator('opa-in-memory').getAttribute('data-running'), 'true');
    await action(page, 'stop').click();
    assert.match(await page.locator('[data-result]').innerText(), /Agreement bits\s+\d/);
    await exerciseSliders(page);
    await action(page, 'reset').click();
    assert.match(await page.locator('[data-result]').innerText(), /Exact for this vector/);
  }));

test('Chip 15 edits every layer size and runs hybrid inference with per-layer errors', { timeout: 45000 }, () =>
  open(15, 1280, async page => {
    const zeroError = await page.locator('[data-chart]').innerText();
    for (const [layer, size] of [[0, 16], [1, 12], [2, 6]]) {
      await field(page, 'layer').selectOption(String(layer));
      assert.equal(await action(page, 'weight').count(), size);
      await action(page, 'weight').nth(size - 1).click();
      await field(page, 'weight').press('Home');
      assert.equal(await action(page, 'weight').nth(size - 1).innerText(), '-1.0000');
    }
    await field(page, 'preset').selectOption('degraded');
    await field(page, 'activation').selectOption('tanh');
    await field(page, 'bits').selectOption('2');
    await field(page, 'detectorBits').selectOption('8');
    await action(page, 'start').click();
    assert.equal(await page.locator('opa-stored-network').getAttribute('data-running'), 'true');
    assert.notEqual(await page.locator('[data-chart]').innerText(), zeroError);
    assert.match(await page.locator('[data-output]').innerText(), /Higher score/);
    await action(page, 'stop').click();
    await exerciseSliders(page);
    await action(page, 'reset').click();
    assert.equal(await page.locator('[data-chart]').innerText(), zeroError);
  }));

test('all three experiments fit phone, tablet and desktop widths', { timeout: 45000 }, async () => {
  for (const chip of [13, 14, 15]) {
    for (const width of [360, 768, 1280]) await open(chip, width, async () => {});
  }
});
