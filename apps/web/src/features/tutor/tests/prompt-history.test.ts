import assert from "node:assert/strict";
import test from "node:test";
import { createPromptHistory, historyDirection } from "../lib/prompt-history.ts";

test("TUTOR-REQ-022 prompt history traverses and restores an empty or typed draft/caret", () => {
  for (const text of ["", "My unsent draft"]){
    const state=createPromptHistory(), caret={start:Math.min(3,text.length),end:Math.min(3,text.length)};
    assert.equal(state.move("up",["First question","Latest question"],text,caret)?.text,"Latest question");
    assert.equal(state.move("up",[],"Latest question",caret)?.text,"First question");
    assert.equal(state.move("up",[],"First question",caret)?.text,"First question");
    assert.equal(state.move("down",[],"First question",caret)?.text,"Latest question");
    assert.deepEqual(state.move("down",[],"Latest question",caret),{text,caret});
    assert.equal(state.move("down",[],text,caret),undefined);
  }
});

test("TUTOR-REQ-022 reset makes edited recall a new draft and snapshots only passed prompts", () => {
  const state=createPromptHistory(),caret={start:0,end:0};
  assert.equal(state.move("up",["Earlier","Latest"],"Draft",caret)?.text,"Latest");
  state.reset();
  assert.equal(state.move("up",["Earlier","Latest"],"Edited latest",caret)?.text,"Latest");
  assert.equal(state.move("down",[],"Latest",caret)?.text,"Edited latest");
  state.reset();
  assert.equal(state.move("up",["New chat only"],"",caret)?.text,"New chat only");
  assert.equal(state.move("up",["Foreign prompt"],"New chat only",caret)?.text,"New chat only");
});

test("TUTOR-REQ-022 empty history never takes over native arrows", () => {
  const state=createPromptHistory();
  assert.equal(state.move("up",["","  "],"draft",{start:0,end:0}),undefined);
  assert.equal(state.move("down",["Older"],"draft",{start:0,end:0}),undefined);
});

test("TUTOR-REQ-022 multiline, selection, modifiers and IME retain native editing", () => {
  const base={key:"ArrowUp",value:"first\nsecond",start:0,end:0};
  assert.equal(historyDirection(base),"up");
  assert.equal(historyDirection({...base,start:7,end:7}),undefined);
  assert.equal(historyDirection({...base,key:"ArrowDown",start:0,end:0}),undefined);
  assert.equal(historyDirection({...base,key:"ArrowDown",start:12,end:12}),"down");
  assert.equal(historyDirection({...base,start:0,end:3}),undefined);
  assert.equal(historyDirection({...base,modified:true}),undefined);
  assert.equal(historyDirection({...base,composing:true}),undefined);
  assert.equal(historyDirection({...base,key:"Enter"}),undefined);
});
