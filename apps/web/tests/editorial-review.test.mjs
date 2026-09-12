import assert from 'node:assert/strict';
import test from 'node:test';
import { fieldCorrections, sectionSubmission } from '../app/editorial/review-draft.ts';

const race = { key: 'example', ballotTitle: 'Example Office', candidates: [{ ballotLabel: 'Example Canddate', partyLabel: 'Independent' }] };
const draft = { decision: 'flagged', note: '', editing: true, edits: { 'ballotLabel:0': 'Example Candidate' } };

test('field correction preserves original and identifies exactly one candidate', () => {
  assert.deepEqual(fieldCorrections(race, draft), [{ field: 'ballotLabel', candidateIndex: 0, value: 'Example Candidate' }]);
  assert.equal(race.candidates[0].ballotLabel, 'Example Canddate');
});
test('only explicitly chosen sections are submitted with separate notes', () => {
  const result = sectionSubmission([race, { ...race, key: 'other' }], { example: draft });
  assert.equal(result.length, 1);
  assert.equal(result[0].raceKey, 'example');
  assert.equal(result[0].corrections.length, 1);
});
test('empty flags and blank corrections cannot submit', () => {
  assert.throws(() => sectionSubmission([race], { example: { ...draft, edits: {}, editing: false } }), /Add a note/);
  assert.throws(() => sectionSubmission([race], { example: { ...draft, edits: { 'ballotLabel:0': ' ' } } }), /1–255/);
});
test('accepted sections do not send an old flag note or stale corrections', () => {
  const [value] = sectionSubmission([race], { example: { ...draft, decision: 'accepted', note: 'Old issue' } });
  assert.deepEqual(value, { raceKey: 'example', decision: 'accepted', note: '', corrections: [] });
});
test('unchanged field is not a correction and unknown section fails', () => {
  assert.deepEqual(fieldCorrections(race, { ...draft, edits: { 'ballotLabel:0': 'Example Canddate' } }), []);
  assert.throws(() => sectionSubmission([], { example: draft }), /no longer/);
});
