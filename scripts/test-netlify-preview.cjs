const { test } = require('node:test');
const assert = require('node:assert/strict');
const { execFileSync, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { previewRequested } = require('./netlify-preview.cjs');

test('ordinary changes and production contexts do not authorize Netlify builds', () => {
  for (const context of [undefined, '', 'production', 'deploy-preview', 'branch-deploy']) {
    assert.equal(previewRequested(context, 'Unify link styling'), false);
  }
  for (const context of [undefined, '', 'production']) {
    assert.equal(previewRequested(context, '[build preview]'), false);
  }
});

test('only explicit preview requests authorize build contexts, and skip takes precedence', () => {
  for (const context of ['deploy-preview', 'branch-deploy']) {
    assert.equal(previewRequested(context, 'Requested review\n\n[build preview]'), true);
    assert.equal(previewRequested(context, '[BUILD PREVIEW]'), true);
    assert.equal(previewRequested(context, '[build preview] [skip netlify]'), false);
    assert.equal(previewRequested(context, '[build preview] [skip ci]'), false);
  }
});

test('CLI enforces request-only builds, including hooks and unreadable commits', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'wearc-preview-'));
  try {
    fs.mkdirSync(path.join(directory, 'scripts'));
    const script = path.join(directory, 'scripts/netlify-preview.cjs');
    fs.copyFileSync(path.join(__dirname, 'netlify-preview.cjs'), script);
    // A harmless fixture proves authorization without building or deploying a site.
    fs.writeFileSync(path.join(directory, 'scripts/build-preview-site.sh'), 'echo built > build-ran\n');
    execFileSync('git', ['init', '--quiet', directory]);
    const commit = (message) => execFileSync('git', ['-C', directory, '-c', 'user.name=Test',
      '-c', 'user.email=test@example.com', 'commit', '--allow-empty', '--quiet', '-m', message]);
    const env = { ...process.env, CONTEXT: 'deploy-preview', COMMIT_REF: '' };
    const run = (mode) => spawnSync(process.execPath, [script, mode], { env, encoding: 'utf8' });
    const marker = path.join(directory, 'build-ran');
    commit('Ordinary change');
    assert.equal(run('--ignore').status, 0);
    assert.equal(run('--build').status, 1);
    assert.equal(fs.existsSync(marker), false);
    commit('Requested review [build preview]');
    assert.equal(run('--ignore').status, 1);
    assert.equal(run('--build').status, 0);
    assert.equal(fs.existsSync(marker), true);
    fs.unlinkSync(marker);
    env.CONTEXT = 'production';
    assert.equal(run('--ignore').status, 0);
    assert.equal(run('--build').status, 1);
    assert.equal(fs.existsSync(marker), false);
    env.CONTEXT = 'deploy-preview';
    env.COMMIT_REF = '0'.repeat(40);
    assert.equal(run('--ignore').status, 0);
    assert.equal(run('--build').status, 1);
    assert.equal(fs.existsSync(marker), false);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
