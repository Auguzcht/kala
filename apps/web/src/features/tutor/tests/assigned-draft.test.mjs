import assert from "node:assert/strict";
import test from "node:test";
import { createAssignedTutorDraft, readAssignedTutorDraft } from "../lib/assigned-draft.ts";

test("TUTOR-REQ-018 assigned draft includes only course topic and fresh identity", () => {
  const draft = createAssignedTutorDraft("course", "  Cloud cost comparison  ");
  assert.match(draft.text, /^Help me understand Cloud cost comparison\./);
  assert.match(draft.text, /key ideas.*example/);
  assert.deepEqual(Object.keys(draft).sort(), ["courseId", "id", "text"]);
  assert.notEqual(draft.id, createAssignedTutorDraft("course", "Cloud cost comparison").id);
  assert.deepEqual(readAssignedTutorDraft({ assignedTutorDraft: draft }, "course"), draft);
});

test("TUTOR-REQ-018 navigation handoff rejects malformed and other-course state", () => {
  const draft = createAssignedTutorDraft("course", "Cloud cost comparison");
  for (const state of [null, {}, { assignedTutorDraft: { ...draft, id: "invalid" } },
    { assignedTutorDraft: { ...draft, text: 3 } }, { assignedTutorDraft: { ...draft, text: " " } }]) {
    assert.equal(readAssignedTutorDraft(state, "course"), null);
  }
  assert.equal(readAssignedTutorDraft({ assignedTutorDraft: draft }, "other-course"), null);
});
