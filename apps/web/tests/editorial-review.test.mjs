import assert from 'node:assert/strict';
import test from 'node:test';
import { editTranscription, fieldCorrections, sectionSubmission } from '../app/editorial/review-draft.ts';

const race = { key: 'example', ballotTitle: 'Example Office', candidates: [{ ballotLabel: 'Example Canddate', partyLabel: 'Independent' }] };
const draft = { decision: 'flagged', note: '', editing: true, edits: { 'ballotLabel:0': 'Example Candidate' } };
const flagged = { decision: 'flagged', note: '', editing: false, edits: {} };

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

test('selecting Flag allows inline corrections without a separate edit mode action', () => {
  const edited = editTranscription(race, flagged, 'ballotLabel:0', 'Example Candidate');
  const [section] = sectionSubmission([race], { example: edited });
  assert.equal(section.decision, 'flagged');
  assert.equal(section.note, '');
  assert.deepEqual(section.corrections, [{ field: 'ballotLabel', candidateIndex: 0, value: 'Example Candidate' }]);
  assert.equal(race.candidates[0].ballotLabel, 'Example Canddate');
});

test('prefilled unchanged fields do not create a review on focus or blur', () => {
  assert.equal(editTranscription(race, undefined, 'ballotTitle', race.ballotTitle), undefined);
  assert.equal(editTranscription(race, undefined, 'ballotLabel:0', race.candidates[0].ballotLabel), undefined);
  assert.deepEqual(sectionSubmission([race], {}), []);
});

test('title, name and party edits accumulate and target the correct candidate', () => {
  const multiple = { ...race, candidates: [...race.candidates, { ballotLabel: 'Second Candidate', partyLabel: 'Green' }] };
  let edited = editTranscription(multiple, flagged, 'ballotTitle', 'Correct Office');
  edited = editTranscription(multiple, edited, 'ballotLabel:0', 'Correct Name');
  edited = editTranscription(multiple, edited, 'partyLabel:1', 'Independent');
  assert.deepEqual(fieldCorrections(multiple, edited), [
    { field: 'ballotTitle', value: 'Correct Office' },
    { field: 'ballotLabel', candidateIndex: 0, value: 'Correct Name' },
    { field: 'partyLabel', candidateIndex: 1, value: 'Independent' },
  ]);
});

test('typing the original value back cancels a correction without accepting the section', () => {
  const edited = editTranscription(race, flagged, 'ballotTitle', 'Correct Office');
  assert.deepEqual(editTranscription(race, edited, 'ballotTitle', race.ballotTitle), flagged);
});

test('unselected or accepted sections cannot be edited or implicitly flagged', () => {
  const accepted = { decision: 'accepted', note: '', editing: false, edits: {} };
  for (const [field, value] of [['ballotTitle', 'Correct Office'], ['ballotLabel:0', 'Correct Name'], ['partyLabel:0', 'Green']]) {
    assert.equal(editTranscription(race, undefined, field, value), undefined);
    assert.equal(editTranscription(race, accepted, field, value), accepted);
    assert.equal(editTranscription(race, undefined, field, value, { decision: 'accepted', note: '' }), undefined);
  }
});

test('reverting a correction preserves flag notes and explicit unsaved flags', () => {
  const flagged = { decision: 'flagged', note: 'Source issue still exists', editing: false, edits: {} };
  const edited = editTranscription(race, flagged, 'ballotTitle', 'Correct Office');
  assert.deepEqual(editTranscription(race, edited, 'ballotTitle', race.ballotTitle), flagged);
  assert.equal(editTranscription(race, undefined, 'ballotTitle', 'Correct Office', { decision: 'flagged', note: 'Saved issue' }).note, 'Saved issue');
});

test('typing spaces is preserved, blur normalization cancels whitespace-only edits', () => {
  const edited = editTranscription(race, flagged, 'ballotTitle', race.ballotTitle + ' ');
  assert.equal(edited.edits.ballotTitle, race.ballotTitle + ' ');
  assert.deepEqual(editTranscription(race, edited, 'ballotTitle', edited.edits.ballotTitle.trim()), flagged);
  assert.throws(() => editTranscription(race, flagged, 'unknown', 'value'), /Unknown correction/);
});

test('choosing Accept overrides a saved Flag and locks further edits', () => {
  const saved = { decision: 'flagged', note: 'Previously flagged' };
  const accepted = { decision: 'accepted', note: '', editing: false, edits: {} };
  assert.equal(editTranscription(race, accepted, 'ballotTitle', 'Changed title', saved), accepted);
});
