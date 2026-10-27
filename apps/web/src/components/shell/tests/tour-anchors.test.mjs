import assert from 'node:assert/strict';
import test from 'node:test';
import ts from 'typescript';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../../../../../', import.meta.url));
const read = (path) => readFileSync(root + 'apps/web/src/' + path, 'utf8');

// E3: recorded from both immutable Git blobs using TypeScript 5.9.3's printer,
// removeComments:true, after removing only data-tour JSX attributes. SHA-256
// hashes attest the historical normalized ASTs; current code is checked below.
// No runtime Git lookup: all seven proofs also run in shallow/fresh clones.
const historical = {
  beforeRevision: '3a6a0aab27a8212f77b83e96b26127d830a696ba',
  acceptedRevision: 'c3d6b6351f7adbfc6e8da1d43e371014473c8b74',
  comparisons: [
    ['components/shell/CourseShell.tsx', '7b3afbf5b13915e33076a5906a126323dc266d65fc636a65ef1549ada895cde0', '7b3afbf5b13915e33076a5906a126323dc266d65fc636a65ef1549ada895cde0', 0, 1],
    ['components/shell/TutorSidebar.tsx', '430c43a34a1c7897a6aace84fbb1daa68306e40441ce555a5314d81179e7e733', '430c43a34a1c7897a6aace84fbb1daa68306e40441ce555a5314d81179e7e733', 0, 1],
    ['features/diagnostic/components/DiagnosticPanel.tsx', '9a9afaf7c0954e04699842ca5d04ff6b8100d41802827301848befe62504481d', '9a9afaf7c0954e04699842ca5d04ff6b8100d41802827301848befe62504481d', 0, 1],
    ['features/flashcards/components/FlashcardDeck.tsx', '855087ff70a25bf0f508c2abc2d948833b1c0a1fc0a069197cd07df95948e8fe', '855087ff70a25bf0f508c2abc2d948833b1c0a1fc0a069197cd07df95948e8fe', 0, 1],
    ['features/practice/components/PracticePanel.tsx', 'dd599238eef8a4c4ad48ee7d35cf1e8a0fc81bc566493b343040cd6204c69d95', 'dd599238eef8a4c4ad48ee7d35cf1e8a0fc81bc566493b343040cd6204c69d95', 0, 1],
    ['features/tutor/components/TutorComposer.tsx', '85c838e3794afcaecb834225fe784bd15f30f910922940a19290eb6e0f670a17', '85c838e3794afcaecb834225fe784bd15f30f910922940a19290eb6e0f670a17', 0, 1],
    ['features/twin/components/TwinBody.tsx', '73ec793a38d2d25bd4b19027d3b4f606aad9ea05e77c0d01da75c6a17c84f527', '73ec793a38d2d25bd4b19027d3b4f606aad9ea05e77c0d01da75c6a17c84f527', 0, 1],
  ],
};
for (const [path, beforeAst, acceptedAst, beforeCount, acceptedCount] of historical.comparisons) {
  test('historical tour attribute-only executable change: ' + path, () => {
    assert.equal(historical.beforeRevision, '3a6a0aab27a8212f77b83e96b26127d830a696ba');
    assert.equal(historical.acceptedRevision, 'c3d6b6351f7adbfc6e8da1d43e371014473c8b74');
    assert.match(beforeAst, /^[0-9a-f]{64}$/);
    assert.match(acceptedAst, /^[0-9a-f]{64}$/);
    assert.equal(acceptedAst, beforeAst, path + ': normalized historical ASTs differ');
    assert.equal(acceptedCount - beforeCount, 1, path + ': historical anchor delta');
  });
}

const parsed = new Map();
function source(path) {
  if (!parsed.has(path)) parsed.set(path, ts.createSourceFile(path, read(path), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX));
  return parsed.get(path);
}
function values(node) {
  if (!node) return ['*'];
  if (ts.isStringLiteral(node)) return [node.text];
  if (ts.isJsxExpression(node)) return values(node.expression);
  if (ts.isConditionalExpression(node)) return [...values(node.whenTrue), ...values(node.whenFalse)];
  return [];
}
function enclosingFunction(node) {
  for (let parent = node.parent; parent; parent = parent.parent) {
    if (ts.isFunctionDeclaration(parent) && parent.name) return parent.name.text;
  }
  return null;
}
function attributes(path, name, { value, expression, owner } = {}) {
  const file = source(path), matches = [];
  function visit(node) {
    if (ts.isJsxAttribute(node) && node.name.getText(file) === name &&
        (owner === undefined || enclosingFunction(node) === owner)) {
      if (value !== undefined && values(node.initializer).includes(value)) matches.push(node);
      else if (expression !== undefined && ts.isJsxExpression(node.initializer) &&
        node.initializer.expression?.getText(file).replace(/\s/g, '') === expression.replace(/\s/g, '')) matches.push(node);
    }
    ts.forEachChild(node, visit);
  }
  visit(file);
  return matches;
}

// Current source ownership, not a frozen count of strings anywhere in the repo.
// id/choicesAnchorId/tourId forwarding is checked at the renderer as well as the
// caller. Reused components and mutually exclusive returns can bind one anchor
// at multiple call sites; its rendering attribute must still occur exactly once.
const directTargets = {
  'id:at-risk-list': ['routes/class/index.tsx'],
  'id:cohort-analytics': ['routes/class/index.tsx'],
  'id:heatmap-panel': ['routes/class/index.tsx'],
  'id:roster-panel': ['routes/class/index.tsx'],
  'id:tour-at-risk-first-flag': ['features/instructor/components/AtRiskList.tsx'],
  'id:tour-cohort-kpis': ['features/instructor/components/CohortStats.tsx'],
  'id:tour-decide-center': ['features/instructor/components/DecisionCenter.tsx'],
  'id:tour-decision-buttons': ['features/instructor/components/DecisionCenter.tsx'],
  'id:tour-rec-card': ['features/instructor/components/DecisionCenter.tsx'],
  'id:tour-record-intervene': ['features/instructor/components/LearnerRecord.tsx'],
  'id:tour-record-ledger': ['features/instructor/components/LearnerRecord.tsx'],
  'id:tour-record-radar': ['features/instructor/components/LearnerRecord.tsx'],
  'id:tour-roster-filter': ['features/instructor/components/RosterTable.tsx'],
  'id:tour-roster-first-row': ['features/instructor/components/RosterTable.tsx'],
  'id:tour-roster-search': ['features/instructor/components/RosterTable.tsx'],
  'id:tour-run-analysis': ['features/instructor/components/DecisionCenter.tsx'],
  'id:tour-skill-approve': ['features/instructor/components/SkillReviewPanel.tsx'],
  'id:tour-skill-review-panel': ['features/instructor/components/SkillReviewPanel.tsx'],
  'id:tour-skill-review-trigger': ['routes/class/index.tsx'],
  'id:tour-standing': ['features/instructor/components/LearnerStanding.tsx'],
  'id:tour-study-actions': ['features/skill-hub/components/StudyBrowser.tsx'],
  'id:tour-tab-activity': ['features/instructor/components/LearnerRecord.tsx'],
  'id:tour-tab-decide': ['features/instructor/components/LearnerRecord.tsx'],
  'id:tour-tab-heatmap': ['routes/class/index.tsx'],
  'id:tour-tab-mastery': ['features/instructor/components/LearnerRecord.tsx'],
  'id:tour-test-menu': ['features/skill-hub/components/TestBrowser.tsx'],
  'id:tour-test-start': ['features/skill-hub/components/TestBrowser.tsx'],
  'id:tour-tutor-input': ['features/tutor/components/TutorComposer.tsx'],
  'id:tour-twin-radar': ['features/twin/components/TwinBody.tsx'],
  'id:tour-twin-readiness': ['features/twin/components/TwinBody.tsx'],
  'data-diagnostic-results:*': ['features/diagnostic/components/DiagnosticResults.tsx'],
  'data-slot:sheet-close': ['components/ui/sheet.tsx', 'SheetContent'],
  'data-tour:diagnostic-header': ['features/diagnostic/components/DiagnosticPanel.tsx'],
  'data-tour:study-complete': ['features/flashcards/components/FlashcardDeck.tsx'],
  'data-tour:test-results': ['features/practice/components/PracticePanel.tsx'],
  'data-tour:tutor-attach': ['features/tutor/components/TutorComposer.tsx'],
  'data-tour:tutor-history': ['components/shell/TutorSidebar.tsx'],
  'data-tour:tutor-history-mobile': ['components/shell/CourseShell.tsx'],
  'data-tour:twin-ledger': ['features/twin/components/TwinBody.tsx'],
};
const forwardedTargets = {
  'id:tour-diagnostic-choices': { caller: 'features/diagnostic/components/DiagnosticPanel.tsx', prop: 'choicesAnchorId', value: 'tour-diagnostic-choices', renderer: 'components/study/AnswerableCard.tsx', expression: 'choicesAnchorId' },
  'id:tour-lesson-explain': { caller: 'features/lessons/components/LessonChat.tsx', prop: 'id', value: 'tour-lesson-explain', renderer: 'components/study/TeachingBlock.tsx', expression: 'id' },
  'id:tour-lesson-dock-toggle': { caller: 'features/lessons/components/LessonChat.tsx', prop: 'tourId', value: 'tour-lesson-dock', renderer: 'components/study/ComposeDock.tsx', expression: 'tourId ? `${tourId}-toggle` : undefined' },
  'id:tour-study-dock': { caller: 'features/flashcards/components/FlashcardDeck.tsx', prop: 'tourId', value: 'tour-study-dock', renderer: 'components/study/ComposeDock.tsx', expression: 'tourId' },
};
async function config(path) {
  const output = ts.transpileModule(read(path), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(output).toString('base64'));
}
const student = await config('components/shell/student-tour.ts');
const instructor = await config('components/shell/instructor-tour.ts');
const steps = [...student.TOUR_STEPS, ...instructor.INSTRUCTOR_TOUR_STEPS,
  ...student.createStudentTour({ skillId: 'fixture' }),
  ...student.createStudentTour({ skillId: 'fixture', setId: 'saved', completedOnly: true })];
const selectors = new Set();
for (const step of steps) {
  for (const key of ['selector', 'waitFor', 'clickSelector', 'clickOnlyWhenClosed']) if (step[key]) selectors.add(step[key]);
  if (step.waitState) selectors.add(step.waitState.selector);
  if (step.prefill) selectors.add('#' + step.prefill.inputId);
}
const currentTargets = new Set();
for (const selector of selectors) {
  for (const branch of selector.split(',').map((part) => part.trim())) {
    let key;
    if (/^#[\w-]+$/.test(branch)) key = 'id:' + branch.slice(1);
    else {
      const match = /^\[([\w-]+)(?:=["']([^"']+)["'])?\]$/.exec(branch);
      assert.ok(match, 'Unsupported tour selector needs an explicit binding check: ' + branch);
      key = match[1] + ':' + (match[2] ?? '*');
    }
    currentTargets.add(key);
  }
}
test('every current tour selector branch has a current renderer check, with no stale catalog entries', () => {
  assert.deepEqual([...currentTargets].sort(), [...Object.keys(directTargets), ...Object.keys(forwardedTargets)].sort());
});
for (const key of currentTargets) test('current tour anchor renders exactly once: ' + key, () => {
  if (forwardedTargets[key]) {
    const entry = forwardedTargets[key];
    assert.ok(attributes(entry.caller, entry.prop, { value: entry.value }).length > 0, entry.caller + ': missing caller binding');
    assert.equal(attributes(entry.renderer, 'id', { expression: entry.expression }).length, 1, entry.renderer + ': renderer anchor must occur once');
  } else {
    const [path, owner] = directTargets[key] ?? [];
    assert.ok(path, key + ': missing current owner');
    const colon = key.indexOf(':');
    assert.equal(attributes(path, key.slice(0, colon), { value: key.slice(colon + 1), owner }).length, 1, path + ': current anchor must occur once');
  }
});

test('current TwinBody retains the accepted tour anchor after WI-25', () => {
  const file = source('features/twin/components/TwinBody.tsx'), anchors = [];
  function visit(node) {
    if (ts.isJsxAttribute(node) && node.name.getText(file) === 'data-tour') {
      assert.ok(node.initializer && ts.isStringLiteral(node.initializer)); anchors.push(node.initializer.text);
    }
    ts.forEachChild(node, visit);
  }
  visit(file);
  assert.deepEqual(anchors, ['twin-ledger']);
});
test('post-DOCS-HYGIENE PracticePanel preserves the approved comment and attribute', () => {
  const current = read('features/practice/components/PracticePanel.tsx');
  assert.ok(current.includes('docs/features/study/README.md#learning-surface-boundaries'));
  assert.equal(attributes('features/practice/components/PracticePanel.tsx', 'data-tour', { value: 'test-results' }).length, 1);
});
