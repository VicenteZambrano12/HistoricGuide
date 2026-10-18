import assert from 'node:assert/strict';
import { test } from 'node:test';
import { parsePdfSources, pdfSourceHref } from './pdfSources.js';

test('PDF links preserve the physical page and encode document path segments', () => {
  const source = { source: 'Pantheon/historic/A guide #1?.pdf', page: 7 };
  assert.equal(pdfSourceHref(source),
    '/api/documents/Pantheon/historic/A%20guide%20%231%3F.pdf#page=7');
});

test('references deduplicate chunks on the same page, not distinct pages', () => {
  const first = { source: 'Pantheon/historic/guide.pdf', page: 7 };
  const second = { ...first, page: 8 };
  assert.deepEqual(parsePdfSources([first, { ...first }, second]), [first, second]);
  assert.deepEqual(parsePdfSources([]), []);
});

test('malformed paths and invalid page numbers fail explicitly', () => {
  for (const source of [
    null, {}, 'guide.pdf', [{ source: 'guide.pdf' }],
    ...[0, -1, 1.5, '2', null].map((page) => [{ source: 'guide.pdf', page }]),
    ...['../guide.pdf', '/guide.pdf', 'a/../guide.pdf', 'a//guide.pdf',
      'a\\guide.pdf', 'guide.txt', 'guide\n.pdf'].map((path) => [{ source: path, page: 1 }])
  ]) {
    assert.throws(() => parsePdfSources(source), /Invalid PDF source/);
  }
});
