import assert from 'node:assert/strict';
import test from 'node:test';
import { reviewPages, firstUnfinishedPage, pageAfterSubmission } from '../app/editorial/review-navigation.ts';

const race = (key, sourcePage, reviewStatus = 'unreviewed') => ({ key, sourcePage, reviewStatus });

test('opening a county skips fully saved reviewed pages', () => {
  const races = [race('one', '70', 'reviewed'), race('two', '71', 'reviewed'), race('three', '72')];
  assert.equal(firstUnfinishedPage(races), '72');
  assert.equal(reviewPages(races)[0].complete, true);
});

test('shared review status counts as complete without inventing local decisions', () => {
  const races = [{ ...race('one', '1', 'reviewed'), decisions: [], countySourceReviewed: false }, race('two', '2')];
  assert.equal(firstUnfinishedPage(races), '2');
  assert.deepEqual(races[0].decisions, []);
  assert.equal(races[0].countySourceReviewed, false);
});

test('a page with any unreviewed or flagged section is not complete', () => {
  for (const status of ['unreviewed', 'flagged']) {
    const races = [race('one', '1', 'reviewed'), race('two', '1', status), race('three', '2')];
    assert.equal(firstUnfinishedPage(races), '1');
    assert.equal(pageAfterSubmission(races, '1'), '1');
    assert.equal(reviewPages(races)[0].reviewed, 1);
  }
});

test('successful completion moves forward past reviewed pages', () => {
  const races = [race('one', '1', 'reviewed'), race('two', '2', 'reviewed'), race('three', '3')];
  assert.equal(pageAfterSubmission(races, '1'), '3');
});

test('after the last page, return only to unfinished work, never a reviewed page', () => {
  const races = [race('one', '1'), race('two', '2', 'reviewed'), race('three', '3', 'reviewed')];
  assert.equal(pageAfterSubmission(races, '3'), '1');
});

test('all complete returns the overview instead of reopening page one', () => {
  const races = [race('one', '1', 'reviewed'), race('two', '2', 'reviewed')];
  assert.equal(firstUnfinishedPage(races), null);
  assert.equal(pageAfterSubmission(races, '2'), null);
});

test('unsaved acceptances do not count as reviewed', () => {
  const pages = reviewPages([race('one', '1')], { one: { decision: 'accepted' } });
  assert.equal(pages[0].complete, false);
  assert.equal(pages[0].reviewed, 0);
  assert.equal(pages[0].pending, 1);
});

test('pending edits keep a saved reviewed page accessible as unfinished', () => {
  const pages = reviewPages([race('one', '1', 'reviewed')], { one: { decision: 'flagged', note: 'Check again' } });
  assert.equal(pages[0].complete, false);
  assert.equal(pages[0].pending, 1);
});

test('page ordering follows source order and supports nonnumeric citations', () => {
  const races = [race('one', '10', 'reviewed'), race('two', 'Appendix B'), race('three', '2')];
  assert.deepEqual(reviewPages(races).map(page => page.sourcePage), ['10', 'Appendix B', '2']);
  assert.equal(pageAfterSubmission(races, '10'), 'Appendix B');
});

test('empty datasets and missing current page are handled safely', () => {
  assert.deepEqual(reviewPages([]), []);
  assert.equal(firstUnfinishedPage([]), null);
  assert.equal(pageAfterSubmission([], ''), null);
  assert.equal(pageAfterSubmission([race('one', '1')], 'missing'), '1');
});
