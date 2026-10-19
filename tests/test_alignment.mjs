// Run with SDK packages linked in an isolated project:
// node tests/test_alignment.mjs /path/project/packages/reviewed-alignment/activation.mjs /path/installed/@hypit/hypit
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
// Match the installed CLI's source-Distribution bootstrap; no global modifications.
const distribution = process.argv[3];
if (distribution) {
  const {register} = await import(pathToFileURL(`${distribution}/node_modules/tsx/dist/esm/api/index.mjs`));
  register();
  const {installDistributionPackageResolution} = await import(pathToFileURL(`${distribution}/packages/loader/src/node/distribution-resolution.ts`));
  installDistributionPackageResolution([distribution]);
}
const {reviewedAlignment} = await import(pathToFileURL(process.argv[2]));
const narrative = {
  id: 'story', segments: [{id: 'speech', startAnchorId: 's', endAnchorId: 'e', tokenStart: 0, tokenEndExclusive: 2}],
  tokens: [{id: 'a', text: '观', segmentId: 'speech', startAnchorId: 'a-s', endAnchorId: 'a-e'},
           {id: 'b', text: '点', segmentId: 'speech', startAnchorId: 'b-s', endAnchorId: 'b-e'}],
};
const segment = {kind: 'segment', id: 'speech', narrativeId: 'story'};
const domain = {id: 'cut-media', frameRate: {numerator: 30, denominator: 1}, frameCount: 300};
const timing = {fps: 30, frames: 300, words: [{text: '观', start: 2, end: 2.4}, {text: '点', start: 2.5, end: 2.9}]};
const boundary = (a, id) => a.boundaries.find(b => b.id === id).frame;
const result = reviewedAlignment(narrative, segment, domain, timing);
assert.equal(boundary(result, 'a-s'), 60);
assert.equal(boundary(result, 'b-e'), 87);
assert.equal(boundary(result, 'e'), 300);
const shifted = reviewedAlignment(narrative, segment, domain,
  {...timing, words: timing.words.map(w => ({...w, start: w.start-1, end: w.end-1}))});
assert.equal(boundary(shifted, 'a-s'), 30);
assert.equal(boundary(shifted, 'b-e'), 57);
assert.throws(() => reviewedAlignment({...narrative, tokens: [{...narrative.tokens[0], text: '论'}, narrative.tokens[1]]}, segment, domain, timing), /Script differs/);
const rewritten = {...narrative, tokens: [{...narrative.tokens[0], text: '论'}, narrative.tokens[1]]};
const fresh = reviewedAlignment(rewritten, segment, domain, {...timing, words: [
  {text: '论', start: 3, end: 3.4}, {text: '点', start: 3.5, end: 3.9}]});
assert.equal(boundary(fresh, 'a-s'), 90); assert.equal(boundary(fresh, 'b-e'), 117);
assert.throws(() => reviewedAlignment(narrative, segment, {...domain, frameCount: 240}, timing), /clock changed/);
// Coarse Chinese word evidence retains one measured envelope, no fake character time.
const coarse = reviewedAlignment(narrative, segment, domain, {...timing, words: [{text: '观点', start: 2, end: 2.9}]});
assert.equal(boundary(coarse, 'a-s'), 60); assert.equal(boundary(coarse, 'b-s'), 60);
assert.equal(boundary(coarse, 'a-e'), 87); assert.equal(boundary(coarse, 'b-e'), 87);
console.log('PASS: measured anchors, changed cut timing, changed speech rejection, rewritten speech with fresh anchors, changed media clock rejection, Chinese coarse envelope (6 checks)');
