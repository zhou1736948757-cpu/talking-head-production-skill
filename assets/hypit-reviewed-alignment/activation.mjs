// Project-authored adapter using Hypit's public SDK. No upstream source is bundled.
import { createMarkupSurfaceFacet, textAttribute, assertAttributes, assertEmptyElement } from '@hypit/hypit/markup';
import { createProducerPackageFacet } from '@hypit/hypit/producer';
import { sealGraphFragment } from '@hypit/hypit/author';
import { sameType } from '@hypit/hypit/protocol';
import { narrativeTypes } from '@hypit/narrative';
import { temporalTypes } from '@hypit/temporal';
import { narrativeTemporalTypes, sealNarrativeAlignment } from '@hypit/narrative-temporal';

const moduleRef = {name: '@koubo/reviewed-alignment', version: '1'};
const timingType = {module: moduleRef, name: 'Timing'};
const align = {module: moduleRef, name: 'reviewed-alignment'};
const absent = {module: moduleRef, name: 'require-reviewed-timing'};
const ports = [
  {name: 'narrative', type: narrativeTypes.narrative},
  {name: 'segment', type: narrativeTypes.segmentRef},
  {name: 'domain', type: temporalTypes.localDomain},
  {name: 'timing', type: timingType},
];
const inline = record => {
  if (record?.value.kind !== 'inline') throw new Error('Reviewed alignment requires inline evidence');
  return record.value.value;
};
const norm = text => text.normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');

export function reviewedAlignment(narrative, segmentRef, domain, timing) {
  const segment = narrative.segments.find(s => s.id === segmentRef.id);
  if (!segment || segmentRef.narrativeId !== narrative.id) throw new Error('Segment identity mismatch');
  const native = narrative.tokens.slice(segment.tokenStart, segment.tokenEndExclusive);
  if (timing.frames !== domain.frameCount || timing.fps !== domain.frameRate.numerator / domain.frameRate.denominator)
    throw new Error('Edited-media clock changed: realign actual final media');
  if (native.map(t => norm(t.text)).join('') !== timing.words.map(w => norm(w.text)).join(''))
    throw new Error('Script differs from accepted recording: fresh evidence and anchors required');
  let cursor = 0, previousStart = 0, previousEnd = 0;
  const evidence = timing.words.map(w => {
    if (!Number.isFinite(w.start) || !Number.isFinite(w.end) || w.start < previousStart || w.end < previousEnd || w.start < 0 || w.end <= w.start || w.end * timing.fps > timing.frames + 0.01)
      throw new Error('Invalid measured token window');
    previousStart = w.start; previousEnd = w.end;
    const start = cursor; cursor += norm(w.text).length;
    return {...w, charStart: start, charEnd: cursor};
  });
  const boundaries = [
    {id: segment.startAnchorId, frame: 0},
    {id: segment.endAnchorId, frame: domain.frameCount},
  ];
  cursor = 0;
  const tokens = native.map(token => {
    const start = cursor; cursor += norm(token.text).length;
    const group = evidence.filter(w => w.charStart < cursor && w.charEnd > start);
    if (!group.length) throw new Error(`No measured evidence for ${token.id}`);
    // A Han word can contain several native tokens. Share its measured envelope;
    // never interpolate invented character times. Author scene markers only at
    // imported-token boundaries; captions for a coarse word highlight as a group.
    const a = Math.round(group[0].start * timing.fps);
    const b = Math.round(group.at(-1).end * timing.fps);
    if (b <= a) throw new Error('Token shorter than one frame; choose a finer program clock');
    boundaries.push({id: token.startAnchorId, frame: a}, {id: token.endAnchorId, frame: b});
    return {tokenId: token.id, segmentId: segment.id, text: token.text,
      startBoundaryId: token.startAnchorId, endBoundaryId: token.endAnchorId};
  });
  return sealNarrativeAlignment({narrativeId: narrative.id, domainId: domain.id,
    segment: {segmentId: segment.id, startBoundaryId: segment.startAnchorId, endBoundaryId: segment.endAnchorId},
    tokens, boundaries}, domain);
}

const fragment = sealGraphFragment({
  inputs: ports,
  operations: [
    {id: 'align', producer: align, inputs: Object.fromEntries(ports.map(p => [p.name,
      {kind: 'fragment-input', name: p.name}])),
    result: {kind: 'output', name: 'alignment'}},
  ],
  exports: [{name: 'alignment', type: narrativeTemporalTypes.narrativeAlignment, root: {kind: 'fragment-operation', operation: 'align'}}],
});
const timingFragment = sealGraphFragment({inputs: [], operations: [
  {id: 'timing', producer: absent, inputs: {}, result: {kind: 'output', name: 'timing'}},
], exports: [{name: 'timing', type: timingType, root: {kind: 'fragment-operation', operation: 'timing'}}]});
const declaration = {name: 'alignment', tag: 'Alignment', mode: 'structured', outputs: [narrativeTemporalTypes.narrativeAlignment]};
const timingDeclaration = {name: 'timing', tag: 'Timing', mode: 'structured', outputs: [timingType]};
const handler = ({element, resolveReference}) => {
  assertAttributes(element, ['id', 'narrative', 'segment', 'domain', 'timing']); assertEmptyElement(element);
  const id = textAttribute(element, 'id');
  const inputs = Object.fromEntries(ports.map(p => {
    const raw = element.attributes[p.name];
    const ref = raw?.kind === 'reference' ? resolveReference(raw.path) : undefined;
    if (!ref || !sameType(ref.type, p.type)) throw new Error(`Alignment.${p.name}: wrong type`);
    return [p.name, ref.ref];
  }));
  return {records: [], fragments: [fragment], components: [{id, fragment: fragment.id, inputs,
    outputs: {alignment: `${id}.alignment`}, range: element.range}], exports: [`${id}.alignment`]};
};
const timingHandler = ({element}) => {
  assertAttributes(element, ['id']); assertEmptyElement(element);
  const id = textAttribute(element, 'id');
  return {records: [], fragments: [timingFragment], components: [{id, fragment: timingFragment.id,
    inputs: {}, outputs: {timing: `${id}.timing`}, range: element.range}], exports: [`${id}.timing`]};
};
export const hypitPackage = {
  format: 'hypit.package@1',
  modules: [{manifest: {
    format: 'hypit.module@1', ...moduleRef,
    dependencies: [narrativeTypes.narrative, temporalTypes.localDomain, narrativeTemporalTypes.narrativeAlignment]
      .map(type => ({module: type.module})),
    types: [{name: 'Timing'}], capabilities: [],
    producers: [{name: absent.name, inputs: [], outputs: [{name: 'timing', type: timingType}], needs: []},
      {name: align.name, inputs: ports, outputs: [{name: 'alignment', type: narrativeTemporalTypes.narrativeAlignment}], needs: []}],
  }}],
  facets: [createMarkupSurfaceFacet({module: moduleRef, declaration, handler}),
    createMarkupSurfaceFacet({module: moduleRef, declaration: timingDeclaration, handler: timingHandler}),
    createProducerPackageFacet({producers: [
      {producer: absent, handler: () => {throw new Error('No timing supplied; choose reviewed-timing in SVRun. No ASR is called.');}},
      {producer: align, handler: ({inputs}) => ({outputs: {alignment: {kind: 'inline', value:
        reviewedAlignment(inline(inputs.narrative), inline(inputs.segment), inline(inputs.domain), inline(inputs.timing))}}, needs: {}})},
    ]})],
};
export default hypitPackage;
