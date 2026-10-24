/** TUTOR-REQ-001: execute the real component with a deterministic hook harness.
 * Query/API/router and visual shells are isolated; no browser or live service.
 * JSX uses React's runtime, and output is rendered with react-dom/server.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { runInNewContext } from "node:vm";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";
import * as presentation from "../lib/presentation.ts";
import { dockLayout } from "../../../components/ai-elements/dock-layout.ts";
import { apiErrorReason } from "../../../lib/api-error.ts";

const require = createRequire(import.meta.url);
const source = readFileSync(new URL("./TutorChat.tsx", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: {
  module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022,
} }).outputText;
const question = "Explain recursion";
const answer = "A function can call itself.";

function messagePair(prefix = "new", q = question, a = answer) {
  return [
    { id: `${prefix}-user`, role: "user", content: q, style: null },
    { id: `${prefix}-answer`, role: "assistant", content: a, style: "default" },
  ];
}

function mount({ messages = [], error, refetch } = {}) {
  const state = [];
  const effects = [];
  let cursor = 0;
  let pending = false;
  let mutationTask;
  let tree;
  let search = { conversation: "conversation-1" };
  let askCalls = 0;
  const toasts = [];
  const active = { data: { id: "conversation-1", messages, attachments: [] }, isLoading: false };
  const hooks = {
    useState(initial) {
      const index = cursor++;
      if (!(index in state)) state[index] = typeof initial === "function" ? initial() : initial;
      return [state[index], (value) => {
        state[index] = typeof value === "function" ? value(state[index]) : value;
      }];
    },
    useRef(initial) {
      const index = cursor++;
      if (!(index in state)) state[index] = { current: initial };
      return state[index];
    },
    useEffect(effect, dependencies) {
      const index = cursor++;
      const previous = state[index];
      if (!previous || dependencies.some((value, i) => !Object.is(value, previous[i]))) {
        effects.push(effect);
        state[index] = dependencies;
      }
    },
  };
  const queryClient = {
    getQueryData: () => active.data,
    async invalidateQueries({ queryKey }) {
      if (queryKey[0] !== "tutor-conversation") return;
      if (refetch) await refetch(active);
      else active.data = { ...active.data, messages: [...active.data.messages, ...messagePair()] };
    },
  };
  const modules = {
    react: hooks,
    "react/jsx-runtime": require("react/jsx-runtime"),
    "@tanstack/react-query": {
      useQueryClient: () => queryClient,
      useMutation(options) {
        return {
          isPending: pending,
          mutate(variables) {
            pending = true;
            mutationTask = (async () => {
              try {
                const result = await options.mutationFn(variables);
                await options.onSuccess(result, variables);
              } catch (failure) {
                options.onError(failure, variables);
              } finally { pending = false; }
            })();
          },
        };
      },
    },
    "@tanstack/react-router": { useNavigate: () => () => {}, useSearch: () => search },
    sonner: { toast: { error: (...args) => toasts.push(args) } },
    "@/features/tutor/lib/presentation": presentation,
    "@/components/ai-elements/dock-layout": { dockLayout },
    "@/features/tutor/components/TutorComposer": uiModule("TutorComposer"),
    "@/features/tutor/components/TutorWelcome": uiModule("TutorWelcome"),
    "@/features/courses": { useCourse: () => ({ data: { title: "AWS101" } }) },
    "@/lib/auth/AuthProvider": { useSession: () => null },
    "@/lib/utils": { cn: (...parts) => parts.filter(Boolean).join(" ") },
    "@/lib/api-error": { apiErrorReason },
    "@/features/tutor/api/tutor.api": {
      async askTutor() {
        askCalls++;
        if (error) throw error;
        return { answer, conversationId: "conversation-1" };
      },
      createTutorConversation: () => assert.fail("existing conversation should be reused"),
    },
    "@/features/tutor": {
      useTutorConversation: () => active,
      useTutorConversations: () => ({ data: [], isLoading: false }),
      useUploadTutorAttachment: () => ({ isPending: false }),
      useDeleteTutorAttachment: () => ({}),
    },
  };
  function uiModule(name) {
    function Shell(props) {
      return React.createElement("section", null,
        props.text, props.pendingLabel, props.bar, props.children, props.dock);
    }
    Shell.displayName = name;
    return { [name]: Shell };
  }
  const exports = {};
  runInNewContext(compiled, {
    exports,
    window: { setTimeout, clearTimeout },
    require(id) {
      if (id in modules) return modules[id];
      if (id.startsWith("@/components/")) {
        const leaf = id.split("/").at(-1);
        const names = { "empty-state": "EmptyState", button: "Button", "file-text": "FileTextIcon", x: "XIcon", "prompt-input": "PromptInputButton", spinner: "Spinner", shimmer: "Shimmer" };
        return uiModule(names[leaf] ?? leaf);
      }
      throw new Error(`Unmocked component import: ${id}`);
    },
  });
  function render() {
    cursor = 0;
    tree = exports.TutorChat({ courseId: "course-1" });
    while (effects.length) effects.shift()();
    return renderToStaticMarkup(tree);
  }
  function elements(node, name, found = []) {
    if (Array.isArray(node)) {
      for (const child of node) elements(child, name, found);
    } else if (React.isValidElement(node)) {
      if (node.type.displayName === name || node.type === name) found.push(node);
      for (const value of Object.values(node.props)) elements(value, name, found);
    }
    return found;
  }
  render();
  return {
    active, toasts, render,
    async ask(q = question) {
      elements(tree, "TutorComposer")[0].props.onAsk(q);
      await mutationTask;
      return render();
    },
    switchConversation(id) { search = { conversation: id }; render(); return render(); },
    get askCalls() { return askCalls; },
  };
}

test("TUTOR-REQ-001 timeout detail appears inline and in toast with retry", async () => {
  const detail = "The tutor took too long to respond. Please try again.";
  const ui = mount({ error: new Error(`API 503: ${JSON.stringify({ detail, code: "tutor_timeout" })}`) });
  const html = await ui.ask();
  assert.ok(html.includes(detail));
  assert.ok(html.includes("Retry"));
  assert.ok(html.includes(question));
  assert.equal(ui.toasts[0][1].description, detail);
  assert.equal(ui.askCalls, 1);
});

test("TUTOR-REQ-001 non-JSON error retains the safe retry fallback", async () => {
  const ui = mount({ error: new Error("API 503: <html>Gateway error</html>") });
  const html = await ui.ask();
  assert.ok(html.includes("Check your connection and try again."));
  assert.ok(!html.includes("Gateway error"));
});

test("TUTOR-REQ-001 saved response keeps normal handoff with no duplicate", async () => {
  const ui = mount();
  const html = await ui.ask();
  assert.equal(html.split(answer).length - 1, 1);
  assert.equal(html.split(question).length - 1, 1);
  assert.ok(!html.includes("may not have been saved"));
  assert.ok(!html.includes("Kala couldn't answer"));
  assert.equal(ui.toasts.length, 0);
});

test("TUTOR-REQ-001 missing saved answer remains visible without another ask", async () => {
  const ui = mount({ refetch: async () => {} });
  const html = await ui.ask();
  assert.ok(html.includes(answer));
  assert.ok(html.includes("This answer may not have been saved."));
  assert.ok(!html.includes("Retry"));
  assert.equal(ui.askCalls, 1);
});

test("TUTOR-REQ-001 failed refetch cannot turn a returned answer into an ask error", async () => {
  const ui = mount({ refetch: async () => { throw new Error("mock refetch failed"); } });
  const html = await ui.ask();
  assert.ok(html.includes(answer));
  assert.ok(!html.includes("Retry"));
  assert.equal(ui.toasts.length, 0);
  assert.equal(ui.askCalls, 1);
});

test("TUTOR-REQ-001 late persistence replaces local copy without duplication", async () => {
  const ui = mount({ refetch: async () => {} });
  await ui.ask();
  ui.active.data = { ...ui.active.data, messages: messagePair() };
  const html = ui.render();
  assert.equal(html.split(answer).length - 1, 1);
  assert.equal(html.split(question).length - 1, 1);
  assert.ok(!html.includes("may not have been saved"));
  assert.equal(ui.askCalls, 1);
});

test("TUTOR-REQ-001 old identical pair cannot be mistaken for this turn's save", async () => {
  const ui = mount({ messages: messagePair("old"), refetch: async () => {} });
  const html = await ui.ask();
  assert.equal(html.split(answer).length - 1, 2);
  assert.ok(html.includes("may not have been saved"));
});

test("TUTOR-REQ-001 returned local answers survive another ask and stay in their conversation", async () => {
  const ui = mount({ refetch: async () => {} });
  await ui.ask();
  const html = await ui.ask("A follow-up question");
  assert.ok(html.includes(question) && html.includes("A follow-up question"));
  assert.equal(html.split(answer).length - 1, 2);
  ui.active.data = { ...ui.active.data, messages: [] };
  assert.ok(!ui.switchConversation("conversation-2").includes(answer));
});


test("TUTOR-REQ-001 saved timestamp ties do not duplicate a returned answer", async () => {
  const ui = mount({ refetch: async (active) => {
    active.data = { ...active.data, messages: messagePair().reverse() };
  } });
  const html = await ui.ask();
  assert.equal(html.split(answer).length - 1, 1);
  assert.ok(!html.includes("may not have been saved"));
});
