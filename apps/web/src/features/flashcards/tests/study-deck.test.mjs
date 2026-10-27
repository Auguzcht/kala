/**
 * APPROVAL-01 component interaction tests without a shared test/config edit.
 * Uses real React hooks/renderer; provider hooks and UI shells are mocked.
 * Install matching react/react-test-renderer in an isolated directory, then:
 * KALA_STUDY_TEST_DEPS=/path/to/test-deps node --experimental-vm-modules --test \
 *   apps/web/src/features/flashcards/tests/study-deck.test.mjs
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { SourceTextModule, SyntheticModule } from 'node:vm';
import { test } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const requireWeb = createRequire(resolve(here, '../../../../package.json'));
const requireTests = process.env.KALA_STUDY_TEST_DEPS
  ? createRequire(resolve(process.env.KALA_STUDY_TEST_DEPS, 'package.json')) : requireWeb;
const React = requireTests('react');
const { create, act } = requireTests('react-test-renderer');
const ts = requireWeb('typescript');
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
globalThis.window = { addEventListener() {}, removeEventListener() {}, setTimeout, clearTimeout };

async function mountDeck({ cards = [card('first'), card('second')], tracked = cards.length, deferRating = false, hasMore = false, mode = 'review', nextCards, deferNew = false, nextError = false, dueAt = '2099-11-02T08:30:00Z', failFirstRating = false } = {}) {
  const calls = { reviews: [], refetches: 0, newFetches: 0 };
  let resolveNew;
  const data = { courseId: 'course', cards, stats: { tracked, due: cards.length, learning: 0, mastered: 0 },
    mode, sessionId: 'session', hasMore };
  const deckHook = { data, isLoading: false, isError: false, isFetching: false,
    refetch: async () => { calls.refetches++; return { data }; } };
  let pendingRating;
  const reviewHook = { isPending: false, mutate(args, options) {
    calls.reviews.push(args);
    if (failFirstRating && calls.reviews.length === 1) options.onError();
    else if (deferRating) { reviewHook.isPending = true; pendingRating = options; }
    else options.onSuccess({ dueAt });
  } };
  function shell(props) { return React.createElement('section', null, props.bar, props.children, props.dock); }
  function dock({ primary, secondary }) {
    return React.createElement('nav', null, ...[primary, secondary].filter(Boolean).map((action) =>
      React.createElement('button', { key: action.label, onClick: action.onClick, disabled: action.disabled }, action.label)));
  }
  const values = {
    useSession: () => ({ userId: 'student' }), readReviewProgress: () => null, writeReviewProgress() {},
    useGetNewFlashcards: () => async () => {
      calls.newFetches++;
      if (deferNew) await new Promise(resolve => { resolveNew = resolve; });
      if (nextError) throw new Error('Synthetic unavailable');
      return { ...data, mode: 'review', sessionId: `next-${calls.newFetches}`, cards: nextCards ?? cards };
    },
    useFlashcardDeck: () => deckHook, useFlashcardMembership: () => ({ data: { counts: { new: 0 } } }),
    useReviewFlashcard: () => reviewHook, usePracticeSetResults: () => ({}),
    useBankStatus: () => ({ data: { bankServing: true, skills: [{ skillId: 'skill', usable: true, status: 'ready' }] } }),
    useTwin: () => ({ data: { skills: [] } }), useTutorAsk: () => ({ isPending: false, mutate() {} }),
    useReducedMotion: () => true, celebrateOnce() {}, cn: (...args) => args.filter(Boolean).join(' '),
    toast: { info() {}, success() {}, error() {} },
    cardStatePresentation: () => ({ className: '', label: 'New' }),
    ComposeDock: dock, StudySurface: shell, SessionState: shell,
    EmptyState: ({ title, description, action }) => React.createElement('section', null,
      React.createElement('h1', null, title), description, action),
    Button: ({ children, onClick, disabled }) => React.createElement('button', { onClick, disabled }, children),
    motion: new Proxy({}, { get: (_, tag) => tag }),
  };
  const file = resolve(here, '../components/FlashcardDeck.tsx');
  const source = readFileSync(file, 'utf8');
  const ast = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const exportsByImport = new Map();
  for (const statement of ast.statements) {
    if (!ts.isImportDeclaration(statement)) continue;
    const bindings = statement.importClause?.namedBindings;
    if (bindings && ts.isNamedImports(bindings)) exportsByImport.set(statement.moduleSpecifier.text,
      bindings.elements.map((element) => element.propertyName?.text ?? element.name.text));
  }
  const module = new SourceTextModule(ts.transpileModule(source, {
    compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText, { identifier: file });
  await module.link((specifier) => {
    const actual = specifier === 'react' ? React
      : specifier === 'react/jsx-runtime' ? requireTests('react/jsx-runtime') : null;
    const names = actual ? Object.keys(actual) : exportsByImport.get(specifier);
    assert.ok(names, `unmocked import ${specifier}`);
    return new SyntheticModule(names, function () {
      for (const name of names) this.setExport(name, actual ? actual[name] : values[name] ?? shell);
    });
  });
  await module.evaluate();
  let renderer;
  await act(async () => { renderer = create(React.createElement(module.namespace.FlashcardDeck,
    { courseId: 'course', onExit() {}, mode })); });
  function button(label) { return renderer.root.findAllByType('button').find((node) => node.children.join('') === label); }
  async function click(label) {
    const node = button(label);
    assert.ok(node, `missing action: ${label}`);
    assert.ok(!node.props.disabled, `action disabled: ${label}`);
    await act(async () => node.props.onClick());
  }
  return { calls, button, click, finishRating: async () => act(async () => {
      reviewHook.isPending = false; pendingRating.onSuccess({ dueAt });
      renderer.update(React.createElement(module.namespace.FlashcardDeck, { courseId: 'course', onExit() {}, mode }));
    }), replaceServerDeck: async (next) => act(async () => {
      deckHook.data = { ...data, ...next };
      renderer.update(React.createElement(module.namespace.FlashcardDeck, { courseId: 'course', onExit() {}, mode }));
    }), finishNew: async () => act(async () => { resolveNew(); }), text: () => JSON.stringify(renderer.toJSON()),
    unmount: async () => act(async () => renderer.unmount()) };
}
function card(id) { return { itemId: id, skillId: 'skill', skillName: 'Skill', prompt: `Prompt ${id}`,
  back: { label: `Answer ${id}`, explanation: '' }, state: 'new', box: 0 }; }
async function recall(deck, rating = 'Got it') { await deck.click('Show answer'); await deck.click(rating); }

test('STUDY-REQ-003 replay starts at card 1 and sends zero additional review POSTs, including a local requeue', async () => {
  const deck = await mountDeck();
  await recall(deck);
  await recall(deck);
  assert.deepEqual(deck.calls.reviews.map((args) => args.itemId), ['first', 'second']);
  assert.ok(deck.button('Go through these again'));
  assert.ok(deck.button('Get new cards'));
  await deck.click('Go through these again');
  assert.match(deck.text(), /Practice round · Your review schedule will not change/);
  assert.match(deck.text(), /Prompt first/);
  assert.equal(deck.calls.refetches, 0);
  await recall(deck, 'Still learning');
  await recall(deck);
  await recall(deck); // first card's local second look
  assert.match(deck.text(), /Practice complete/);
  assert.equal(deck.calls.reviews.length, 2);
  await deck.click('Go through these again'); // repeated replay also stays local
  await recall(deck);
  await recall(deck);
  assert.equal(deck.calls.reviews.length, 2);
  await deck.click('Get new cards');
  assert.equal(deck.calls.newFetches, 1);
  assert.match(deck.text(), /No new cards right now/);
  assert.equal(deck.calls.reviews.length, 2);
  await deck.unmount();
});

test('STUDY-REQ-003 one-card replay explicitly resets its terminal state', async () => {
  const deck = await mountDeck({ cards: [card('only')] });
  await recall(deck);
  await deck.click('Go through these again');
  assert.ok(deck.button('Show answer'));
  await recall(deck);
  assert.match(deck.text(), /Practice complete/);
  assert.equal(deck.calls.reviews.length, 1);
  assert.equal(deck.calls.refetches, 0);
  await deck.unmount();
});

test('STUDY-REQ-003 replay waits for the final rating to finish saving', async () => {
  const deck = await mountDeck({ cards: [card('only')], deferRating: true });
  await recall(deck);
  assert.equal(deck.button('Go through these again').props.disabled, true);
  assert.equal(deck.button('Get new cards').props.disabled, true);
  await deck.finishRating();
  assert.equal(Boolean(deck.button('Go through these again').props.disabled), false);
  await deck.click('Go through these again');
  await recall(deck);
  assert.equal(deck.calls.reviews.length, 1);
  await deck.unmount();
});

test('STUDY-REQ-005 empty ready course distinguishes caught up from no cards', async () => {
  const caughtUp = await mountDeck({ cards: [], tracked: 2 });
  assert.match(caughtUp.text(), /All caught up/);
  assert.doesNotMatch(caughtUp.text(), /Preparing questions/);
  await caughtUp.unmount();
  const empty = await mountDeck({ cards: [], tracked: 0 });
  assert.match(empty.text(), /No cards yet/);
  assert.doesNotMatch(empty.text(), /All caught up/);
  await empty.unmount();
});

for (const mode of ['review', 'all']) {
  for (const nextCards of [[], [card('only')]]) {
    test(`STUDY-REQ-006 ${mode} empty or duplicate-only refresh keeps completion and rating guard`, async () => {
      const deck = await mountDeck({ cards: [card('only')], mode, nextCards });
      await recall(deck);
      await deck.click('Get new cards');
      assert.match(deck.text(), /Study complete/);
      assert.match(deck.text(), /No new cards right now. Your next review is/);
      assert.match(deck.text(), /2099/);
      assert.doesNotMatch(deck.text(), /Prompt only/);
      assert.equal(deck.calls.reviews.length, 1);
      await deck.click('Get new cards');
      assert.equal(deck.calls.newFetches, 2);
      assert.equal(deck.calls.reviews.length, 1);
      await deck.click('Go through these again');
      await recall(deck);
      assert.equal(deck.calls.reviews.length, 1);
      await deck.click('Get new cards');
      assert.match(deck.text(), /No new cards right now/);
      assert.equal(deck.calls.reviews.length, 1);
      await deck.unmount();
    });
  }
}

test('STUDY-REQ-006 delayed mixed refresh stays complete then serves only unseen cards', async () => {
  const deck = await mountDeck({ cards: [card('first'), card('second')],
    nextCards: [card('first'), card('third'), card('second')], deferNew: true });
  await recall(deck); await recall(deck);
  await deck.click('Get new cards');
  assert.match(deck.text(), /Study complete/);
  assert.equal(deck.button('Get new cards').props.disabled, true);
  assert.equal(deck.button('Go through these again').props.disabled, true);
  assert.equal(deck.calls.newFetches, 1);
  await deck.finishNew();
  assert.match(deck.text(), /Prompt third/);
  assert.doesNotMatch(deck.text(), /Prompt first|Prompt second/);
  await recall(deck);
  assert.deepEqual(deck.calls.reviews.map(args => args.itemId), ['first', 'second', 'third']);
  assert.equal(new Set(deck.calls.reviews.map(args => args.idempotencyKey)).size, 3);
  assert.ok(deck.calls.reviews.every(args => args.sessionId && args.latencyMs >= 0));
  await deck.click('Go through these again');
  await recall(deck);
  assert.equal(deck.calls.reviews.length, 3);
  await deck.unmount();
});

test('STUDY-REQ-006 a genuinely new one-card deck can be rated once after completion', async () => {
  const deck = await mountDeck({ cards: [card('first')], nextCards: [card('next')] });
  await recall(deck); await deck.click('Get new cards');
  assert.match(deck.text(), /Prompt next/);
  await recall(deck);
  assert.deepEqual(deck.calls.reviews.map(args => args.itemId), ['first', 'next']);
  await deck.click('Get new cards');
  assert.match(deck.text(), /Study complete/);
  assert.match(deck.text(), /No new cards right now/);
  assert.equal(deck.calls.reviews.length, 2);
  await deck.unmount();
});

test('STUDY-REQ-006 refresh failure keeps completion and permits retry', async () => {
  const deck = await mountDeck({ cards: [card('only')], nextError: true });
  await recall(deck); await deck.click('Get new cards');
  assert.match(deck.text(), /Study complete/);
  assert.match(deck.text(), /We could not check for new cards. Try again./);
  assert.equal(Boolean(deck.button('Get new cards').props.disabled), false);
  assert.equal(deck.calls.reviews.length, 1);
  await deck.unmount();
});

for (const dueAt of [undefined, 'invalid']) {
  test(`STUDY-REQ-006 missing or invalid scheduling date is never fabricated: ${dueAt}`, async () => {
    const deck = await mountDeck({ cards: [card('only')], nextCards: [], dueAt: dueAt ?? null });
    await recall(deck); await deck.click('Get new cards');
    assert.match(deck.text(), /Study complete/);
    assert.match(deck.text(), /We could not read your next review date/);
    assert.doesNotMatch(deck.text(), /Your next review is/);
    await deck.unmount();
  });
}

test('STUDY-REQ-003 failed review retries with the same first-rating idempotency key', async () => {
 const deck = await mountDeck({cards:[card('only')], failFirstRating:true});
 await recall(deck);
 assert.match(deck.text(),/Prompt only/);
 await deck.click('Got it');
 assert.equal(deck.calls.reviews.length,2);
 assert.equal(deck.calls.reviews[0].idempotencyKey,deck.calls.reviews[1].idempotencyKey);
 assert.equal(deck.calls.reviews[0].sessionId,deck.calls.reviews[1].sessionId);
 await deck.click('Go through these again'); await recall(deck);
 assert.equal(deck.calls.reviews.length,2);
 await deck.unmount();
});

test('STUDY-REQ-006 background query replacement cannot replay completed cards', async () => {
 const deck = await mountDeck({ cards: [card('only')] });
 await recall(deck);
 await deck.replaceServerDeck({sessionId:'background',cards:[card('only')]});
 assert.match(deck.text(), /Study complete/);
 assert.doesNotMatch(deck.text(), /Prompt only/);
 await deck.click('Go through these again'); await recall(deck);
 assert.equal(deck.calls.reviews.length,1);
 await deck.unmount();
});

test('STUDY-REQ-005 an initially empty deck can recover into available cards', async () => {
 const deck = await mountDeck({cards:[],tracked:0});
 assert.match(deck.text(),/No cards yet/);
 await deck.replaceServerDeck({sessionId:'available',cards:[card('ready')]});
 assert.match(deck.text(),/Prompt ready/);
 await recall(deck);
 assert.equal(deck.calls.reviews.length,1);
 await deck.unmount();
});

test('STUDY-REQ-006 repeated activation before rerender issues one due/new fetch', async () => {
 const deck=await mountDeck({cards:[card('only')], nextCards:[], deferNew:true});
 await recall(deck);
 const action=deck.button('Get new cards');
 await act(async()=>{action.props.onClick();action.props.onClick();});
 assert.equal(deck.calls.newFetches,1);
 assert.match(deck.text(),/Study complete/);
 await deck.finishNew();
 assert.match(deck.text(),/No new cards right now/);
 assert.equal(deck.calls.reviews.length,1);
 await deck.unmount();
});
