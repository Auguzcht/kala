import assert from "node:assert/strict";
import test from "node:test";
import { apiErrorReason } from "./api-error.ts";

test("TUTOR-REQ-001 flat detail remains compatible", () => {
  assert.equal(apiErrorReason(new Error('API 502: {"detail":"Please try again."}')), "Please try again.");
});
test("TUTOR-REQ-001 detail plus code displays the retry message", () => {
  assert.equal(apiErrorReason(new Error('API 503: {"detail":"The tutor took too long. Please try again.","code":"tutor_timeout"}')), "The tutor took too long. Please try again.");
});
test("TUTOR-REQ-001 non-JSON body safely uses caller fallback", () => {
  assert.equal(apiErrorReason(new Error("API 503: Service Unavailable")), null);
  assert.equal(apiErrorReason(new Error("API 503: <html>Gateway error</html>")), null);
});
test("TUTOR-REQ-001 JSON escapes and alternate key order parse correctly", () => {
  const body = JSON.stringify({ code: "tutor_timeout", detail: 'Try "again".\nPlease retry.' });
  assert.equal(apiErrorReason(`API 503: ${body}`), 'Try "again". Please retry.');
  assert.equal(apiErrorReason('API 422: {"detail":[{"msg":"invalid"}]}'), null);
});
