import assert from "node:assert/strict";
import test from "node:test";
import {
  groupConversations,
  supportsConversationManagement,
  pickGreeting,
  starterSuggestions,
  dockShape,
  validateTutorFile,
  createConversationResolver,
} from "../lib/presentation.ts";
import { tutorConversationSchema } from "../schema/tutor.schema.ts";

const row = {
  id: "one",
  courseId: "course",
  skillId: null,
  title: "Topic",
  createdAt: "2026-10-25",
  updatedAt: "2026-10-25",
};
test("TUTOR-REQ-005 absence and null remain distinct after boundary parsing", () => {
  assert.equal(
    supportsConversationManagement(tutorConversationSchema.parse(row)),
    false,
  );
  assert.equal(
    supportsConversationManagement(
      tutorConversationSchema.parse({ ...row, pinnedAt: null }),
    ),
    true,
  );
  assert.equal(
    supportsConversationManagement(
      tutorConversationSchema.parse({ ...row, pinnedAt: "2026-10-25" }),
    ),
    true,
  );
});
test("TUTOR-REQ-005 grouping preserves API pin and recent ordering", () => {
  const list = [
    { ...row, id: "pin2", pinnedAt: "2026-10-25" },
    { ...row, id: "pin1", pinnedAt: "2026-10-24" },
    { ...row, id: "recent2", pinnedAt: null },
    { ...row, id: "legacy" },
  ];
  const groups = groupConversations(list);
  assert.deepEqual(
    groups.Pinned.map((x) => x.id),
    ["pin2", "pin1"],
  );
  assert.deepEqual(
    groups.Recents.map((x) => x.id),
    ["recent2", "legacy"],
  );
  assert.deepEqual(groupConversations([]), { Pinned: [], Recents: [] });
});
test("TUTOR-REQ-006 local deterministic day/course greetings use time pools", () => {
  for (const [hour, label] of [
    [9, "Good morning"],
    [15, "Good afternoon"],
    [20, "Good evening"],
    [1, "Up late?"],
  ]) {
    const date = new Date(2026, 9, 25, hour);
    const value = pickGreeting(date, "course", "AWS101");
    assert.equal(value, pickGreeting(new Date(date), "course", "AWS101"));
    assert.ok(value.includes(label));
    assert.ok(!pickGreeting(date, "course").includes("undefined"));
  }
  assert.ok(
    Array.from({ length: 31 }, (_, day) =>
      pickGreeting(new Date(2026, 9, day + 1, 9), "course", "AWS101"),
    ).some((x) => x.includes("AWS101")),
  );
});
test("TUTOR-REQ-008 templates supply 3–4 starters without invented skills", () => {
  assert.deepEqual(starterSuggestions([]), []);
  assert.equal(starterSuggestions([{ name: "Storage" }]).length, 3);
  const starters = starterSuggestions([
    { name: "Storage" },
    { name: "Networking" },
    { name: "Storage" },
  ]);
  assert.equal(starters.length, 4);
  assert.ok(starters.every((x) => /Storage|Networking/.test(x)));
});
test("TUTOR-REQ-009 shape reacts to dragging and persisted attachments", () => {
  assert.equal(dockShape(false, false), "rounded-full");
  for (const [drag, attached] of [
    [true, false],
    [false, true],
    [true, true],
  ])
    assert.equal(dockShape(drag, attached), "rounded-xl");
});
test("TUTOR-REQ-009 constraints match existing backend file support and byte cap", () => {
  for (const name of ["notes.txt", "notes.MD", "notes.pdf"])
    assert.equal(validateTutorFile({ name, size: 5 * 1024 * 1024 }), null);
  assert.match(validateTutorFile({ name: "image.png", size: 1 }), /supported/);
  assert.match(
    validateTutorFile({ name: "notes.pdf", size: 5 * 1024 * 1024 + 1 }),
    /5MB/,
  );
});
test("TUTOR-REQ-009 overlapping attach/send resolves one lazy conversation; failure can retry", async () => {
  let calls = 0;
  let finish;
  const resolve = createConversationResolver();
  const create = () => {
    calls++;
    return new Promise((done) => {
      finish = done;
    });
  };
  const first = resolve(undefined, create),
    second = resolve(undefined, create);
  assert.equal(calls, 1);
  finish("created");
  assert.deepEqual(await Promise.all([first, second]), ["created", "created"]);
  assert.equal(await resolve("active", create), "active");
  const retry = createConversationResolver();
  await assert.rejects(
    retry(undefined, async () => {
      throw new Error("synthetic creation failure");
    }),
  );
  assert.equal(await retry(undefined, async () => "retry"), "retry");
});

test("WI-22 desktop history bounds leave room for the conversation", async () => {
  const { clampTutorHistoryWidth, tutorHistoryMaxWidth } =
    await import("../lib/history-width.ts");
  assert.equal(clampTutorHistoryWidth(200, 1440), 280);
  assert.equal(clampTutorHistoryWidth(800, 1440), 440);
  assert.equal(clampTutorHistoryWidth(320, 1440), 320);
  assert.equal(tutorHistoryMaxWidth(1024), 440);
  assert.ok(1024 - 56 - tutorHistoryMaxWidth(1024) >= 480);
});
