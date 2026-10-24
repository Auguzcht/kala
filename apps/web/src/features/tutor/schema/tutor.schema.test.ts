import assert from "node:assert/strict";
import test from "node:test";
import { tutorErrorSchema } from "./tutor.schema.ts";

test("TUTOR-REQ-001 error code is optional and nullable", () => {
  for (const value of [{ detail: "Retry" }, { detail: "Retry", code: null }, { detail: "Retry", code: "tutor_timeout" }]) {
    assert.deepEqual(tutorErrorSchema.parse(value), value);
  }
});
