import test from 'node:test';
import assert from 'node:assert/strict';
import { describeFunctionTest } from '../../app/static/js/task-viewer/function-test-display.js';

const input = (value) => '# mca:function-test:v1\n' + JSON.stringify(value);
test('function failures show calls students can run', () => {
    assert.equal(describeFunctionTest(input({ function: 'reverse', args: [[1, 2]], mode: 'return' })),
        'result = reverse([1, 2])\nprint(result)');
    assert.equal(describeFunctionTest(input({ function: 'show_positive', args: [[1, -2]], mode: 'print' })),
        'show_positive([1, -2])');
    assert.equal(describeFunctionTest('normal stdin'), null);
    assert.equal(describeFunctionTest('# mca:function-test:v1\ninvalid'), null);
});
