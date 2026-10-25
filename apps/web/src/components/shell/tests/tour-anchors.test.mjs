import assert from 'node:assert/strict';
import test from 'node:test';
import ts from 'typescript';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../../../../../../',import.meta.url));
const paths=['components/shell/CourseShell.tsx','components/shell/TutorSidebar.tsx','features/diagnostic/components/DiagnosticPanel.tsx','features/flashcards/components/FlashcardDeck.tsx','features/practice/components/PracticePanel.tsx','features/tutor/components/TutorComposer.tsx','features/twin/components/TwinBody.tsx'];
function normalize(text){
 const source=ts.createSourceFile('file.tsx',text,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);let attributes=0;
 const transformed=ts.transform(source,[context=>{const visit=node=>{if(ts.isJsxAttribute(node)&&node.name.getText(source)==='data-tour'){attributes++;return undefined;}return ts.visitEachChild(node,visit,context);};return node=>ts.visitNode(node,visit);}]);
 const printed=ts.createPrinter({removeComments:true}).printFile(transformed.transformed[0]);transformed.dispose();return {printed,attributes};
}
const twinPath='features/twin/components/TwinBody.tsx';
// WI-25 legitimately changes TwinBody after the accepted tour-only revision.
const acceptedTourRevision='c3d6b6351f7adbfc6e8da1d43e371014473c8b74';
for(const path of paths)test((path===twinPath?'historical tour attribute-only executable change: ':'attribute-only executable change: ')+path,()=>{
 const before=normalize(execFileSync('git',['show','3a6a0aa:apps/web/src/'+path],{cwd:root,encoding:'utf8'}));
 const after=normalize(path===twinPath
  ?execFileSync('git',['show',acceptedTourRevision+':apps/web/src/'+path],{cwd:root,encoding:'utf8'})
  :readFileSync(root+'apps/web/src/'+path,'utf8'));
 assert.equal(after.printed,before.printed);assert.equal(after.attributes-before.attributes,1);
});
test('current TwinBody retains the accepted tour anchor after WI-25',()=>{
 function anchors(text){
  const source=ts.createSourceFile('file.tsx',text,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);const values=[];
  function visit(node){if(ts.isJsxAttribute(node)&&node.name.getText(source)==='data-tour'){assert.ok(node.initializer&&ts.isStringLiteral(node.initializer));values.push(node.initializer.text);}ts.forEachChild(node,visit);}visit(source);return values;
 }
 const historical=execFileSync('git',['show',acceptedTourRevision+':apps/web/src/'+twinPath],{cwd:root,encoding:'utf8'});
 assert.deepEqual(anchors(historical),['twin-ledger']);
 assert.deepEqual(anchors(readFileSync(root+'apps/web/src/'+twinPath,'utf8')),anchors(historical));
});
test('post-DOCS-HYGIENE PracticePanel preserves the approved comment and attribute',{skip:process.env.KALA_TOUR_REQUIRE_DOCS!=='1'},()=>{
 const source=readFileSync(root+'apps/web/src/features/practice/components/PracticePanel.tsx','utf8');
 assert.ok(source.includes('docs/features/study/README.md#learning-surface-boundaries'));
 assert.ok(source.includes('data-tour="test-results"'));
});
