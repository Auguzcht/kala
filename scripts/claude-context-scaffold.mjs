#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { basename, extname, relative, resolve, sep } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(fileURLToPath(new URL('..', import.meta.url)));
const temporaryDirectory = resolve(tmpdir());
const requestedOutput = process.argv[2] ?? 'kala-claude-context-scaffold.zip';
const outputPath = resolve(temporaryDirectory, requestedOutput);
const maximumFileBytes = 512 * 1024;

// Keep this deliberately limited to current product context and implementation.
// Add paths here only when they materially help Claude understand or change Kala.
const allowedRootFiles = new Set([
  'AGENTS.md', 'CLAUDE.md', 'README.md', 'Makefile', 'package.json',
  'pnpm-workspace.yaml', '.npmrc',
]);
const allowedDocumentation = new Set([
  'docs/masterplan.md',
  'docs/stack.md',
  'docs/architecture.md',
  'docs/BACKEND.md',
  'docs/TESTING.md',
  'docs/UI_AND_MODULES.md',
  'docs/SUPABASE.md',
  'apps/web/README.md',
  'apps/web/src/styles/DESIGN.md',
  'services/api/README.md',
  'services/worker/README.md',
  'infra/blackboard/README.md',
  'infra/terraform/README.md',
]);
const allowedDirectory = /^(?:apps\/web\/(?:src|public)|services\/(?:api|worker)\/(?:app|scripts)|packages\/db\/migrations|supabase\/functions)\//;
const excludedPath = /(^|\/)(?:node_modules|\.git|\.agents|\.codex|\.claude|\.cache|\.venv|venv|dist|build|coverage|\.tanstack|__pycache__|\.pytest_cache|\.ruff_cache|test-results|playwright-report)(\/|$)|(^|\/)(?:\.env(?:\.|$)|.*\.(?:pem|key|p12|pfx|jks|tfstate(?:\.\w+)?|tsbuildinfo|lockb|map|min\.js))$/i;
const excludedName = /(?:^|\/)(?:MEMORY\.md|(?:claude-context(?:-scaffold)?)(?:\.md|\.mjs|\.zip)|(?:openapi\.json|routeTree\.gen\.ts|types\.gen\.ts)|.*\.(?:test|spec)\.[^.]+|.*\.(?:patch|bak|backup))$/i;
const textExtensions = new Set([
  '.cjs', '.css', '.html', '.ini', '.js', '.json', '.md', '.mjs', '.mts',
  '.py', '.sql', '.toml', '.ts', '.tsx', '.txt', '.yaml', '.yml',
]);
const textBasenames = new Set([
  'AGENTS.md', 'CLAUDE.md', 'CONTRIBUTING.md', 'LICENSE', 'README',
  'README.md', 'SECURITY.md',
]);

if (outputPath !== temporaryDirectory && !outputPath.startsWith(`${temporaryDirectory}${sep}`)) {
  throw new Error(`Scaffold ZIP output must stay under ${temporaryDirectory}: ${outputPath}`);
}
if (!outputPath.toLowerCase().endsWith('.zip')) {
  throw new Error('Scaffold output filename must end in .zip.');
}

const candidateFiles = execFileSync(
  'git',
  ['ls-files', '--cached', '--others', '--exclude-standard', '-z'],
  { cwd: repositoryRoot },
).toString('utf8').split('\0').filter(Boolean);

const selectedFiles = candidateFiles
  .filter((filePath) => allowedRootFiles.has(filePath)
    || allowedDocumentation.has(filePath)
    || allowedDirectory.test(filePath))
  .filter((filePath) => !excludedPath.test(filePath) && !excludedName.test(filePath)
    && !filePath.endsWith('/routeTree.gen.ts'))
  .filter((filePath) => textBasenames.has(basename(filePath))
    || textExtensions.has(extname(filePath).toLowerCase()))
  .filter((filePath) => resolve(repositoryRoot, filePath) !== outputPath)
  .sort((left, right) => left.localeCompare(right));

const stagingDirectory = mkdtempSync(resolve(temporaryDirectory, 'kala-claude-context-'));
const includedFiles = [];
const skippedFiles = [];
try {
  for (const filePath of selectedFiles) {
    const contents = readFileSync(resolve(repositoryRoot, filePath));
    if (contents.byteLength > maximumFileBytes
      || contents.subarray(0, Math.min(contents.length, 8192)).includes(0)) {
      skippedFiles.push(filePath);
      continue;
    }
    const normalized = contents.toString('utf8').replaceAll('\r\n', '\n');
    const stagedPath = resolve(stagingDirectory, filePath);
    mkdirSync(resolve(stagedPath, '..'), { recursive: true });
    writeFileSync(stagedPath, normalized, 'utf8');
    includedFiles.push(filePath);
  }

  const manifest = [
    '# Kala Claude context scaffold',
    '',
    'Generated locally by `scripts/claude-context-scaffold.mjs`. This ZIP is disposable working context; repository files remain the source of truth.',
    '',
    `Included files: ${includedFiles.length}.`,
    '',
    'The selection favors repository instructions, product and architecture references, frontend/backend/worker source, and database migrations.',
    'Excluded by design: dependency trees, build/cache output, tests, generated API/type dumps, lockfiles, local memory and operational artifacts, secrets, and binary assets.',
    '',
    '## Included files',
    '',
    ...includedFiles.map((filePath) => `- ${filePath}`),
    '',
    ...(skippedFiles.length ? ['## Skipped for size or binary content', '', ...skippedFiles.map((filePath) => `- ${filePath}`), ''] : []),
  ].join('\n');
  writeFileSync(resolve(stagingDirectory, 'CLAUDE_CONTEXT_SCAFFOLD.md'), manifest, 'utf8');

  rmSync(outputPath, { force: true });
  execFileSync('zip', ['-q', '-r', outputPath, '.'], { cwd: stagingDirectory });
  const sizeBytes = readFileSync(outputPath).byteLength;
  console.log(`Wrote ${outputPath} with ${includedFiles.length} source file(s) (${sizeBytes} bytes).`);
} finally {
  rmSync(stagingDirectory, { recursive: true, force: true });
}
