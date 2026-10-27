import assert from "node:assert/strict";
import test from "node:test";
import {
  groupConversations,
  supportsConversationManagement,
  pickGreeting,
  validateTutorFile,
  createConversationResolver,
  shouldOfferExplanations,
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
test("WI-22 Recents sorting leaves pinned order and source data unchanged", () => {
  const list = [
    { ...row, id: "z", title: "Zebra", updatedAt: "2026-10-25" },
    { ...row, id: "p", pinnedAt: "2026-10-24" },
    { ...row, id: "a", title: "Alpha", updatedAt: "2026-10-24" },
  ];
  assert.deepEqual(
    groupConversations(list).Recents.map((x) => x.id),
    ["z", "a"],
  );
  for (const sort of ["oldest", "title"]) {
    assert.deepEqual(
      groupConversations(list, sort).Recents.map((x) => x.id),
      ["a", "z"],
    );
    assert.deepEqual(
      groupConversations(list, sort).Pinned.map((x) => x.id),
      ["p"],
    );
  }
  assert.deepEqual(
    list.map((x) => x.id),
    ["z", "p", "a"],
  );
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


test("TUTOR-REQ-021 casual latest turns do not offer explanation chips", () => {
  for (const question of ["Hello!", "Hi Kala", "Good morning", "Hi, how are you?", "Thanks!", "Thank you so much", "Okay", "Got it", "Bye!", "Who are you?", "What's your name?", "What can you do?", "Can you help me?", "Tell me a joke", "How's the weather?", "What time is it?", "Salamat!", "Kumusta?"]) {
    assert.equal(shouldOfferExplanations(question, "Hello! I’m glad you’re here. What would you like to learn or work on today?"), false, question);
  }
});

test("TUTOR-REQ-021 learning requests and mixed greetings keep explanation chips", () => {
  for (const question of ["What is EC2?", "EC2?", "Explain cloud computing", "Hi, can you explain S3?", "Thanks, what about databases?", "Explain your last answer in more detail", "What does 'hello world' mean in programming?"]) {
    assert.equal(shouldOfferExplanations(question, "EC2 provides virtual computers."), true, question);
  }
  assert.equal(shouldOfferExplanations(undefined, "Object storage keeps data as durable objects."), true);
});

test("TUTOR-REQ-021 absent answers and brief acknowledgements have no explanation chips", () => {
  assert.equal(shouldOfferExplanations("Explain storage", undefined), false);
  assert.equal(shouldOfferExplanations("Explain storage", "  "), false);
  assert.equal(shouldOfferExplanations("Tell me something", "Okay!"), false);
});
