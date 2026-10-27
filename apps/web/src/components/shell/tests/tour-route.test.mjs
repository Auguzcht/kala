import assert from 'node:assert/strict';
import test from 'node:test';
import {matchesTourRoute,isTourUiClick} from '../tour-route.ts';
import {createStudentTour,TOUR_STEPS} from '../student-tour.ts';
import {INSTRUCTOR_TOUR_STEPS} from '../instructor-tour.ts';
test('concrete and parameterized routes retain segment boundaries',()=>{
 assert.ok(matchesTourRoute('/class/student/learner','/class/student/$uid'));
 for(const path of ['/class/student','/class/student/$uid','/class/student/a/extra','/class/students/a'])assert.ok(!matchesTourRoute(path,'/class/student/$uid'));
 assert.ok(matchesTourRoute('/course/skill/topic','/course/skill/*'));
 assert.ok(!matchesTourRoute('/course/skill','/course/skill/*'));
 assert.ok(!matchesTourRoute('/course/skills/topic','/course/skill/*'));
 assert.ok(matchesTourRoute('/class','/class'));
});
test('every automatic tour click is a specifically permitted UI operation',()=>{
 for(const step of [...createStudentTour({skillId:'prepared'}),...INSTRUCTOR_TOUR_STEPS])if(step.click)assert.ok(isTourUiClick(step.clickSelector??step.selector),step.selector);
 for(const selector of ['#tour-diagnostic-submit','#tour-skill-approve','#tour-test-start','#tour-run-analysis','#tour-decision-buttons','[data-tour="tutor-attach"]'])assert.ok(!isTourUiClick(selector));
});
test('student tour keeps one prepared skill and no automatic sessions',()=>{
 for(const context of [{skillId:'prepared'},{skillId:'prepared',setId:'saved'},{skillId:'prepared',completedOnly:true}]){
  const steps=createStudentTour(context);
  assert.ok(steps.length<20);
  for(const step of steps.filter(s=>s.route.startsWith('/course/skill/'))){assert.equal(step.route,'/course/skill/prepared');assert.ok(!step.search?.start);assert.ok(!step.click);}
  assert.ok(steps.some(s=>s.selector==='[data-tour="study-complete"]'&&s.optional));
  assert.ok(steps.some(s=>s.selector==='[data-tour="test-results"]'&&s.optional));
 }
 assert.ok(TOUR_STEPS.some(s=>s.selector.includes('tutor-history')));
 assert.ok(TOUR_STEPS.some(s=>s.selector.includes('tutor-attach')));
});
test('TOUR-REQ-009 all 27 instructor steps avoid write clicks and write-completion waits',()=>{
 assert.equal(INSTRUCTOR_TOUR_STEPS.length,27);
 const readWaits=new Set(['#tour-standing','#heatmap-panel','#tour-skill-review-panel','#tour-decide-center','#tour-record-radar','#tour-record-ledger']);
 for(const [index,step] of INSTRUCTOR_TOUR_STEPS.entries()){
  assert.ok(!step.studentAction&&!step.waitState,`step ${index+1} must not require a recorded action`);
  if(step.click)assert.ok(isTourUiClick(step.clickSelector??step.selector),`step ${index+1} clicks only permitted UI`);
  if(step.waitFor)assert.ok(readWaits.has(step.waitFor),`step ${index+1} waits only for read-only UI`);
  assert.ok(!step.description.includes(';'),`step ${index+1} copy has no semicolon`);
 }
 for(const number of [15,20,21,22,25]){
  const step=INSTRUCTOR_TOUR_STEPS[number-1];
  assert.ok(step.explainOnly&&!step.click&&!step.waitFor,`step ${number} explains without waiting for a write control`);
  assert.ok(step.fallbackDescription);
 }
 assert.match(INSTRUCTOR_TOUR_STEPS[14].description,/Approve.*Reject.*Next/);
});

test('TOUR-REQ-009 selects progress beyond page one without hard-coded identities',async()=>{
 const {progressTourLearner,progressLearnerSearch}=await import('../tour-learner.ts');
 const row=(userId,evidenceCount=0,attempts=0)=>({userId,displayName:'Synthetic '+userId,pseudonym:'Learner '+userId,weakestSkillName:'Cloud basics',evidenceCount,attempts,skillsWithEvidence:attempts?1:0});
 const students=[...Array.from({length:23},(_,i)=>row('empty-'+i)),row('measured-small',13,13),row('measured-large',396,381)];
 const roster={courseId:'course',students};
 const learner=progressTourLearner(roster,'course');
 assert.equal(learner.userId,'measured-large');
 assert.equal(students[0].userId,'empty-0');
 assert.equal(progressLearnerSearch(roster,learner),'Learner measured-large');
 assert.equal(progressTourLearner(roster,'other'),undefined);
 assert.equal(progressTourLearner(undefined,'course'),undefined);
 assert.equal(progressTourLearner({courseId:'course',students:students.slice(0,23)},'course'),undefined);
 assert.equal(INSTRUCTOR_TOUR_STEPS[4].progressLearner,'select');
 assert.equal(INSTRUCTOR_TOUR_STEPS[15].progressLearner,'record');
 assert.ok(INSTRUCTOR_TOUR_STEPS[15].explainOnly&&!INSTRUCTOR_TOUR_STEPS[15].click);
 const duplicates={courseId:'course',students:[{...row('a',1),pseudonym:'Same',displayName:'Same'},{...row('b',1),pseudonym:'Same',displayName:'Same'}]};
 assert.equal(progressLearnerSearch(duplicates,duplicates.students[0]),undefined);
 assert.equal(progressTourLearner(duplicates,'course').userId,'a');
});
