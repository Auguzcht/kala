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
