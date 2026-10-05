#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { basename, extname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(fileURLToPath(new URL('..', import.meta.url)));
const outputPath = resolve(repositoryRoot, process.argv[2] ?? 'claude-context.md');
const maximumFileBytes = 512 * 1024;

const excludedPath = /(^|\/)(node_modules|dist|build|coverage|\.git|\.agents|\.codex)(\/|$)|(^|\/)(\.env(?:\.|$)|.*\.(pem|key|p12|pfx|jks))$/i;
const sensitiveName = /(^|\/)(evaluation-data|private-results|secrets?)(\/|$)|(^|\/)(bellaura_architecture_lock\.md|claude-context\.md|claude-context\.mjs)$/i;
const textExtensions = new Set([
  '.cjs', '.css', '.csv', '.html', '.ini', '.js', '.json', '.mjs', '.md',
  '.mts', '.sql', '.svg', '.toml', '.ts', '.tsx', '.txt', '.yaml', '.yml',
]);
const textBasenames = new Set([
  'AGENTS.md', 'CLAUDE.md', 'CONTRIBUTING.md', 'LICENSE', 'README',
  'README.md', 'SECURITY.md', 'tsconfig.json',
]);

const files = execFileSync(
  'git',
  ['ls-files', '--cached', '--others', '--exclude-standard', '-z'],
  { cwd: repositoryRoot },
)
  .toString('utf8')
  .split('\0')
  .filter(Boolean)
  .filter((filePath) => !excludedPath.test(filePath) && !sensitiveName.test(filePath))
  .filter((filePath) => resolve(repositoryRoot, filePath) !== outputPath)
  .filter(
    (filePath) =>
      textBasenames.has(basename(filePath)) ||
      textExtensions.has(extname(filePath).toLowerCase()),
  )
  .sort((left, right) => left.localeCompare(right));

const sections = files
  .map((filePath) => {
    const contents = readFileSync(resolve(repositoryRoot, filePath));

    if (
      contents.byteLength > maximumFileBytes ||
      contents.subarray(0, Math.min(contents.length, 8192)).includes(0)
    ) {
      return null;
    }

    const text = contents
      .toString('utf8')
      .replaceAll('\r\n', '\n')
      .replace(/\n*$/, '\n');

    return `## ${filePath}\n\n\`\`\`text\n${text}\`\`\`\n`;
  })
  .filter(Boolean);

const generated = [
  '# Claude repository context',
  '',
  '> Generated locally by `scripts/claude-context.mjs`; this bundle is disposable and is not a source-of-truth replacement for the files below.',
  '',
  `Included files: ${sections.length}.`,
  '',
  'Preserve repository instructions, contract boundaries, synthetic-data rules, and documented status/evidence claims.',
  '',
  ...sections,
].join('\n');

writeFileSync(outputPath, `${generated.trimEnd()}\n`, 'utf8');
console.log(`Wrote ${relative(repositoryRoot, outputPath)} with ${sections.length} file(s).`);
