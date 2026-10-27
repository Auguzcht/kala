import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const generator = fileURLToPath(new URL('./claude-context.mjs', import.meta.url));
function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'kala-context-test-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const write = (path, content) => {
    mkdirSync(dirname(join(root, path)), { recursive: true });
    writeFileSync(join(root, path), content);
  };
  const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  git('init', '-q');
  git('config', 'user.name', 'Context fixture');
  git('config', 'user.email', 'context@example.test');
  git('config', 'commit.gpgsign', 'false');
  write('scripts/claude-context.mjs', readFileSync(generator));
  write('.gitignore', 'claude-context.md\n');
  for (const path of ['AGENTS.md', 'CLAUDE.md', 'docs/README.md', 'docs/features/README.md', 'docs/engineering/architecture.md']) {
    write(path, `# ${path}\nCommitted core ${path}\n`);
  }
  write('package.json', JSON.stringify({ packageManager: 'pnpm@9', scripts: { dev: 'web dev' } }));
  write('apps/web/package.json', JSON.stringify({ dependencies: { react: '^19' } }));
  write('services/api/app/example.py', 'first\nsecond\n```\nfourth\n');
  write('docs/archive/old.md', 'HISTORICAL_BODY_NOT_DEFAULT\n');
  write('docs/work/demo/evidence/report.md', 'EVIDENCE_BODY_NOT_DEFAULT\n');
  write('.env', 'SYNTHETIC_ENV_NOT_READ\n');
  write('secret.json', 'SYNTHETIC_SECRET_NOT_READ\n');
  const commit = () => { git('add', '.'); git('commit', '-qm', 'fixture snapshot'); return git('rev-parse', 'HEAD'); };
  const sha = commit();
  const run = (...args) => spawnSync(process.execPath, [join(root, 'scripts/claude-context.mjs'), ...args], { cwd: root, encoding: 'utf8' });
  const packet = () => readFileSync(join(root, 'claude-context.md'), 'utf8');
  return { root, write, git, commit, sha, run, packet };
}
function success(result) { assert.equal(result.status, 0, result.stderr); }
function failure(result, pattern) { assert.equal(result.status, 1); assert.match(result.stderr, pattern); }

test('CTX-REQ-001/003: five core sources only, committed snapshot, no remote required', (t) => {
  const f = fixture(t);
  f.write('AGENTS.md', 'UNCOMMITTED_CORE_NOT_READ');
  f.write('notes.md', 'UNTRACKED_NOT_READ');
  success(f.run());
  const packet = f.packet();
  assert.match(packet, new RegExp(f.sha));
  assert.match(packet, /Committed core AGENTS.md/);
  assert.doesNotMatch(packet, /UNCOMMITTED_CORE|UNTRACKED_NOT_READ|HISTORICAL_BODY|EVIDENCE_BODY|SYNTHETIC_ENV|SYNTHETIC_SECRET|first\nsecond/);
  assert.equal((packet.match(/^### .+ — complete$/gm) ?? []).length, 5);
  assert.ok(Buffer.byteLength(packet) <= 64 * 1024);
  assert.match(packet, /remote freshness and publication are unverified/);
});

test('CTX-REQ-002: requested ranges are numbered, bounded and fenced safely', (t) => {
  const f = fixture(t);
  success(f.run('--include', 'services/api/app/example.py:2-3', '--include', 'services/api/app/example.py:2-3'));
  assert.match(f.packet(), /lines 2-3 ONLY/);
  assert.match(f.packet(), /````text\n2: second\n3: ```\n````/);
  assert.doesNotMatch(f.packet(), /1: first|4: fourth/);
  assert.equal((f.packet().match(/ — lines 2-3 ONLY/g) ?? []).length, 1);
});

test('CTX-REQ-002: records require explicit inclusion and retain historical labels', (t) => {
  const f = fixture(t);
  success(f.run('--include', 'docs/archive/old.md', '--include', 'docs/work/demo/evidence/report.md'));
  assert.equal((f.packet().match(/Historical source explicitly requested; not current authority/g) ?? []).length, 2);
  assert.match(f.packet(), /HISTORICAL_BODY_NOT_DEFAULT/);
});

test('CTX-REQ-001: oversized source fails without overwriting previous packet', (t) => {
  const f = fixture(t);
  f.write('large.txt', `small\n${'x'.repeat(25 * 1024)}`); f.commit();
  f.write('claude-context.md', 'KEEP_PREVIOUS_PACKET');
  failure(f.run('--include', 'large.txt'), /exceeds 24 KiB/);
  assert.equal(f.packet(), 'KEEP_PREVIOUS_PACKET');
  success(f.run('--include', 'large.txt:1-1'));
  assert.match(f.packet(), /1: small/);
  assert.doesNotMatch(f.packet(), /x{100}/);
});

test('CTX-REQ-001: total budget fails rather than silently dropping requested sources', (t) => {
  const f = fixture(t);
  for (const name of ['a', 'b', 'c']) f.write(`${name}.txt`, name.repeat(22 * 1024));
  f.commit(); f.write('claude-context.md', 'KEEP_TOTAL');
  failure(f.run('--include', 'a.txt', '--include', 'b.txt', '--include', 'c.txt'), /Packet exceeds 64 KiB/);
  assert.equal(f.packet(), 'KEEP_TOTAL');
});

test('CTX-REQ-003: secret, binary, generated and symlink sources are refused', (t) => {
  const f = fixture(t);
  f.write('null.txt', Buffer.from([0, 1]));
  f.write('invalid.txt', Buffer.from([0xff]));
  f.write('services/api/openapi.json', '{}');
  symlinkSync(join(f.root, '.env'), join(f.root, 'alias.txt'));
  f.commit();
  for (const path of ['.env', 'secret.json', 'services/api/openapi.json']) failure(f.run('--include', path), /Excluded source/);
  failure(f.run('--include', 'alias.txt'), /Not a regular Git text source/);
  failure(f.run('--include', 'null.txt'), /Not a text source/);
  failure(f.run('--include', 'invalid.txt'), /Cannot read UTF-8/);
});

test('CTX-REQ-004: tracked files and symlink destinations cannot be overwritten', (t) => {
  const f = fixture(t);
  const original = readFileSync(join(f.root, 'AGENTS.md'), 'utf8');
  failure(f.run('AGENTS.md'), /tracked project source/);
  symlinkSync(join(f.root, 'AGENTS.md'), join(f.root, 'output.md'));
  failure(f.run('output.md'), /never a directory or symlink/);
  symlinkSync(f.root, join(f.root, 'directory-alias'));
  failure(f.run('directory-alias/AGENTS.md'), /tracked project source/);
  assert.equal(readFileSync(join(f.root, 'AGENTS.md'), 'utf8'), original);
});

test('CTX-REQ-003: explicit ref pins all metadata and sources to that commit', (t) => {
  const f = fixture(t);
  f.write('AGENTS.md', 'NEWER_COMMITTED_CORE'); f.commit();
  success(f.run('--ref', f.sha));
  assert.match(f.packet(), /Committed core AGENTS.md/);
  assert.doesNotMatch(f.packet(), /NEWER_COMMITTED_CORE/);
});

test('CTX-REQ-002/004: missing files, malformed ranges/options/refs fail; custom output works', (t) => {
  const f = fixture(t);
  for (const range of ['0-2', '3-2', '1-100', '9007199254740992-9007199254740993']) {
    failure(f.run('--include', `services/api/app/example.py:${range}`), /Invalid range/);
  }
  failure(f.run('--include', 'missing.txt'), /No tracked file/);
  failure(f.run('--ref', 'not-a-ref'), /Git rev-parse failed/);
  failure(f.run('--include'), /requires a value/);
  failure(f.run('--unknown'), /Unexpected argument/);
  success(f.run('custom.md', '--include', 'services/api/app/example.py'));
  assert.match(readFileSync(join(f.root, 'custom.md'), 'utf8'), /first\nsecond/);
  success(f.run('--help'));
});
