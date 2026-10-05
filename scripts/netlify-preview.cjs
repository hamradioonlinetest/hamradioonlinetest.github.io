/* Netlify builds are allowed only for an explicitly requested preview commit. */
const { execFileSync, spawnSync } = require('node:child_process');
const path = require('node:path');

function previewRequested(context, message) {
  if (!['deploy-preview', 'branch-deploy'].includes(context)) return false;
  if (/\[skip (?:netlify|ci)\]/i.test(message)) return false;
  return /\[build preview\]/i.test(message);
}

function main(mode) {
  const root = path.resolve(__dirname, '..');
  let message = '';
  try {
    const ref = /^[a-f0-9]{40}$/i.test(process.env.COMMIT_REF || '') ? process.env.COMMIT_REF : 'HEAD';
    message = execFileSync('git', ['log', '-1', '--format=%B', ref], { cwd: root, encoding: 'utf8' });
  } catch {
    // Unknown request state must never authorize a build.
  }
  const requested = previewRequested(process.env.CONTEXT, message);
  if (mode === '--ignore') {
    console.log(requested ? 'Explicit preview request: continue.' : 'Netlify preview not requested: skip.');
    return requested ? 1 : 0; // Netlify's ignore-command exit convention.
  }
  if (mode === '--build') {
    // Build hooks can bypass ignore; enforce the request at the build step too.
    if (!requested) {
      console.error('No authorized preview request. Use GitHub Pages for production.');
      return 1;
    }
    const result = spawnSync('bash', ['scripts/build-preview-site.sh'], { cwd: root, stdio: 'inherit' });
    return result.status ?? 1;
  }
  console.error('Usage: netlify-preview.cjs --ignore|--build');
  return 2;
}

module.exports = { previewRequested };
if (require.main === module) process.exitCode = main(process.argv[2]);
