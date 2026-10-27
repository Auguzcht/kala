#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { lstatSync, realpathSync, writeFileSync } from 'node:fs';
import { basename, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// CTX-REQ-001–004. This local Markdown exporter is independent of the scaffold.
const repositoryRoot = resolve(fileURLToPath(new URL('..', import.meta.url)));
const maximumPacketBytes = 64 * 1024;
const maximumSourceBytes = 24 * 1024;
const coreFiles = [
  'AGENTS.md', 'CLAUDE.md', 'docs/README.md',
  'docs/features/README.md', 'docs/engineering/architecture.md',
];
const excludedPath = /(^|\/)(node_modules|dist|build|coverage|\.git|\.agents|\.codex|\.tmp|\.terraform|evaluation-data|private-results|secrets?)(\/|$)|(^|\/)(\.env(?:\.|$)|secret(?:s)?\.json|.*\.(pem|key|p12|pfx|jks|tfstate|map|zip|gz)|.*\.tfstate\..*|.*lock.*\.(json|yaml)|claude-context(?:-scaffold)?(?:\.mjs|\.md|\.zip))$/i;
const generatedSource = /(^|\/)(openapi\.json|routeTree\.gen\.ts|types\.gen\.ts)$|^packages\/schema\/supabase\.ts$/;
const help = `Usage: node scripts/claude-context.mjs [output.md] [options]

Default: write claude-context.md in this checkout (64 KiB maximum).
A holistic overview, not a source dump. Scaffold output is unchanged.
Reads one committed snapshot; never fetches, reads local source edits or calls hosted services.

  --ref REF                  Select a locally available commit/ref (default HEAD)
  --include PATH             Add one complete tracked text source (24 KiB maximum)
  --include PATH:START-END   Add a labeled, numbered excerpt instead
  --help                     Show usage

Examples:
  pnpm context:claude
  node scripts/claude-context.mjs --ref origin/main
  node scripts/claude-context.mjs --include docs/features/tutor/README.md
  node scripts/claude-context.mjs --include services/api/app/main.py:1-60

Extra sources must fit whole; oversized packets fail without replacing old output.
Use the reported SHA with --ref to keep follow-up packets on the same snapshot.
`;

function parseArguments(args) {
  const options = { output: 'claude-context.md', ref: 'HEAD', includes: [] };
  let hasOutput = false;
  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index];
    if (argument === '--help') return null;
    if (argument === '--ref' || argument === '--include') {
      const value = args[++index];
      if (!value || value.startsWith('-')) throw new Error(`${argument} requires a value. See --help.`);
      if (argument === '--ref') options.ref = value;
      else options.includes.push(value);
    } else if (argument.startsWith('-') || hasOutput) {
      throw new Error(`Unexpected argument: ${argument}. See --help.`);
    } else {
      options.output = argument;
      hasOutput = true;
    }
  }
  return options;
}

function git(...args) {
  try {
    return execFileSync('git', args, {
      cwd: repositoryRoot, encoding: 'buffer', maxBuffer: 16 * 1024 * 1024,
      timeout: 30000, stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, GIT_TERMINAL_PROMPT: '0' },
    });
  } catch {
    // Do not echo subprocess output, credentials or file contents on failure.
    throw new Error(`Git ${args[0]} failed; verify the requested local ref/path.`);
  }
}
const textGit = (...args) => new TextDecoder('utf-8', { fatal: true }).decode(git(...args));
const inline = (value) => String(value).replace(/[\r\n|`]/g, ' ');
function fenced(value) {
  const fence = '`'.repeat(Math.max(2, ...(value.match(/`+/g) ?? []).map((match) => match.length)) + 1);
  return `${fence}text\n${value.trimEnd()}\n${fence}`;
}

function main() {
  const options = parseArguments(process.argv.slice(2));
  if (!options) { console.log(help); return; }
  const outputPath = resolve(repositoryRoot, options.output);
  if (!outputPath.endsWith('.md') || excludedPath.test(basename(outputPath).replace(/^claude-context\.md$/, 'packet.md'))) {
    throw new Error('Output must be a disposable Markdown file, not a credential path.');
  }
  try {
    if (!lstatSync(outputPath).isFile()) throw new Error('Output must be a regular file, never a directory or symlink.');
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  let canonicalOutput;
  try { canonicalOutput = realpathSync(outputPath); }
  catch (error) {
    if (error.code !== 'ENOENT') throw error;
    canonicalOutput = resolve(realpathSync(dirname(outputPath)), basename(outputPath));
  }
  const tracked = textGit('ls-files', '--cached', '-z').split('\0').filter(Boolean);
  if (tracked.some((path) => resolve(realpathSync(repositoryRoot), path) === canonicalOutput)) {
    throw new Error('Output is tracked project source; choose a disposable Markdown destination.');
  }

  const revision = textGit('rev-parse', '--verify', '--end-of-options', `${options.ref}^{commit}`).trim();
  const entries = textGit('ls-tree', '-r', '-z', revision).split('\0').filter(Boolean).map((entry) => {
    const tab = entry.indexOf('\t');
    return [entry.slice(tab + 1), entry.slice(0, tab).split(' ')[0]];
  });
  const modes = new Map(entries);
  const files = [...modes.keys()];
  const manifest = [];

  function source(specification) {
    const match = /^(.*):(\d+)-(\d+)$/.exec(specification);
    const path = match ? match[1] : specification;
    if (!modes.has(path)) throw new Error(`No tracked file at ${revision.slice(0, 12)}: ${path}`);
    if (excludedPath.test(path) || generatedSource.test(path)) throw new Error(`Excluded source: ${path}`);
    if (!['100644', '100755'].includes(modes.get(path))) throw new Error(`Not a regular Git text source: ${path}`);
    if (Number(textGit('cat-file', '-s', `${revision}:${path}`)) > 2 * 1024 * 1024) {
      throw new Error(`Source too large to read safely: ${path}; select a smaller task source.`);
    }
    let content;
    try { content = textGit('show', `${revision}:${path}`); }
    catch { throw new Error(`Cannot read UTF-8 text source: ${path}`); }
    if (content.includes('\0')) throw new Error(`Not a text source: ${path}`);
    const lines = content.replaceAll('\r\n', '\n').replace(/\n$/, '').split('\n');
    const first = match ? Number(match[2]) : 1;
    const last = match ? Number(match[3]) : lines.length;
    if (!Number.isSafeInteger(first) || !Number.isSafeInteger(last) || first < 1 || last < first || last > lines.length) {
      throw new Error(`Invalid range for ${path}; file has ${lines.length} lines.`);
    }
    const selected = lines.slice(first - 1, last);
    const rendered = match ? selected.map((line, index) => `${first + index}: ${line}`).join('\n') : selected.join('\n');
    if (Buffer.byteLength(rendered) > maximumSourceBytes) {
      throw new Error(`${path} exceeds 24 KiB; use --include PATH:START-END for a smaller section.`);
    }
    const history = /^docs\/(archive\/|work\/.*\/evidence\/)/.test(path);
    manifest.push(`${path}:${first}-${last}${match ? ' (explicit excerpt)' : ' (complete)'}`);
    return `### ${path}${match ? ` — lines ${first}-${last} ONLY` : ' — complete'}\n\n${history ? 'Historical source explicitly requested; not current authority.\n\n' : ''}${fenced(rendered)}`;
  }

  const sections = [
    '# Kala — Claude project overview',
    `Snapshot: \`${inline(options.ref)}\` at **${revision}**.\n\nCommitted source only; working edits and untracked files are excluded. No fetch was performed; remote freshness and publication are unverified.`,
    '## How to use this packet\n\nRead the repository instructions, documentation guide, feature registry and architecture below in that order. This is a bounded orientation packet, not a full repository, previous-chat recap or feature audit. Links point to the next task-specific document; they do not mean its contents are included. Follow the router for the actual task. If repository access is unavailable, ask Fred for that exact document or line range with --include, rather than requesting every file or guessing omitted requirements.\n\nNo hosted state, deployment, test result, live acceptance or authorization is established here. Do not read archive/evidence unless the task names them. Application bodies, tests, SQL, generated types, lockfiles, local environment and historical records are not embedded by default.',
  ];
  const areas = [
    ['apps/web/src/features/', 'Feature UI, clients, hooks and schemas'],
    ['apps/web/src/components/', 'Shared UI, shell and tour primitives'],
    ['apps/web/src/app/', 'Router and application providers'],
    ['services/api/app/routers/', 'Authenticated HTTP boundaries'],
    ['services/api/app/ai/', 'Provider routing and retrieval'],
    ['services/api/app/learn/', 'Learning and review logic'],
    ['services/api/app/twin/', 'Learning evidence and twin calculations'],
    ['services/worker/app/jobs/', 'Scheduled, resumable jobs'],
    ['packages/db/migrations/', 'Immutable numeric migration history'],
    ['scripts/', 'Local maintenance and verification tools'],
    ['infra/', 'Infrastructure source; not deployed by this exporter'],
  ];
  const counts = areas.map(([path, role]) => `| \`${path}\` | ${files.filter((file) => file.startsWith(path)).length} | ${role} |`);
  const entrypoints = [
    ['apps/web/src/app/router.tsx', 'Web navigation'],
    ['apps/web/src/styles/DESIGN.md', 'Visual authority'],
    ['services/api/app/main.py', 'API composition'],
    ['services/worker/app/handler.py', 'Scheduled worker entry'],
    ['docs/engineering/local-development.md', 'Commands and tooling contracts'],
    ['docs/engineering/security-and-privacy.md', 'Security boundaries and known limits'],
    ['docs/engineering/runbooks/README.md', 'Human-run operational procedures'],
  ].filter(([path]) => modes.has(path)).map(([path, role]) => `- \`${path}\` — ${role} (not embedded)`);
  const rootPackage = JSON.parse(textGit('show', `${revision}:package.json`));
  const webPackage = JSON.parse(textGit('show', `${revision}:apps/web/package.json`));
  const dependencyNames = ['react', 'vite', 'typescript', '@tanstack/react-router', '@tanstack/react-query', 'zustand', '@supabase/supabase-js'];
  const stack = dependencyNames.flatMap((name) => {
    const version = webPackage.dependencies?.[name] ?? webPackage.devDependencies?.[name];
    return version ? [`- ${name}: \`${inline(version)}\` (declared range, not installed version)`] : [];
  });
  const commandNames = ['dev', 'api:dev', 'build', 'lint', 'typecheck', 'context:claude'];
  const commands = commandNames.filter((name) => rootPackage.scripts?.[name])
    .map((name) => `- \`pnpm ${name}\`: \`${inline(rootPackage.scripts[name])}\``);
  sections.push(`## Repository map — metadata, not source\n\nPackage manager: \`${inline(rootPackage.packageManager ?? 'see package.json')}\`.\n\n${stack.join('\n')}\n\n| Area | Tracked files | Responsibility |\n| --- | ---: | --- |\n${counts.join('\n')}\n\nSelected entry points:\n\n${entrypoints.join('\n')}\n\nSelected manifest commands (not executed):\n\n${commands.join('\n')}\n\nThe architecture guide below explains the Blackboard → browser/API → worker/database/model boundaries. Counts and paths establish no implementation correctness or deployment status.`);
  sections.push(`## Core guides — complete source\n\n${coreFiles.map(source).join('\n\n')}`);
  const extras = [...new Set(options.includes)].filter((path) => !coreFiles.includes(path));
  if (extras.length) sections.push(`## Explicit task sources\n\n${extras.map(source).join('\n\n')}`);
  sections.push(`## Coverage and next reading\n\nEmbedded sources:\n\n${manifest.map((path) => `- \`${path}\``).join('\n')}\n\nOnly these sources are embedded. For the next task, repeat --include PATH or --include PATH:START-END; use --ref ${revision} to pin the same snapshot. Complete packet limit: 64 KiB; individual source limit: 24 KiB. Sources are never silently truncated. Split large task reading into smaller packets. The scaffold generator is independent and unchanged.`);
  const generated = `${sections.join('\n\n')}\n`;
  const bytes = Buffer.byteLength(generated);
  if (bytes > maximumPacketBytes) {
    throw new Error(`Packet exceeds 64 KiB (${(bytes / 1024).toFixed(1)} KiB); request fewer/smaller --include ranges. Existing output was not overwritten.`);
  }
  writeFileSync(outputPath, generated, 'utf8');
  console.log(`Wrote ${outputPath}: ${bytes} bytes (${(bytes / 1024).toFixed(1)} KiB), ${manifest.length} embedded source(s), snapshot ${revision.slice(0, 12)}.`);
}

try { main(); } catch (error) {
  console.error(`Context export failed: ${error.message}`);
  process.exitCode = 1;
}
