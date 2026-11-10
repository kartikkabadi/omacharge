const assert = require('node:assert/strict')
const test = require('node:test')
const {parse: parseChargeStatus} = require('../ChargeModel.js')

function snapshot() {
  return {
    version: '0.1.2', installed: true, batteries: [{id: 'BAT0'}], conflicts: [], error: '',
    controls: [{
      id: 'BAT0', driver: 'dell', label: 'Internal battery', kind: 'threshold',
      shared: false, persisted: true, stopValues: [55, 80, 100], startValues: [50, 75, 95],
      derived: '', gap: 5, fullStart: 95, careStop: 80, fullStop: 100,
      end: 80, start: 75, saved: null, warning: ''
    }]
  }
}

test('accepts full snapshots and keeps markup-shaped labels as literal data', () => {
  const data = snapshot()
  data.controls[0].label = '<img src="https://example.invalid/tracker">'
  assert.deepEqual(parseChargeStatus(JSON.stringify(data)), data)
})

test('rejects malformed nested values before QML can bind to them', () => {
  for (const [key, value] of [
    ['id', '../../etc/passwd'], ['stopValues', null], ['stopValues', []],
    ['startValues', [true]], ['stopValues', [80, 55]], ['end', 101],
    ['start', false], ['careStop', 99], ['gap', 0], ['warning', {}],
    ['persisted', 'yes'], ['kind', 'shell-command'], ['driver', 'x'.repeat(81)]
  ]) {
    const data = snapshot()
    data.controls[0][key] = value
    assert.throws(() => parseChargeStatus(JSON.stringify(data)), key)
  }
})

test('rejects truncated, duplicate and oversized responses', () => {
  for (const raw of ['{', 'null', '[]', '{}', ' '.repeat(131073)]) {
    assert.throws(() => parseChargeStatus(raw))
  }
  const data = snapshot()
  data.controls.push({...data.controls[0]})
  assert.throws(() => parseChargeStatus(JSON.stringify(data)))
})

test('allows unknown live limits without inventing a reading', () => {
  const data = snapshot()
  data.controls[0].end = null
  data.controls[0].start = null
  assert.equal(parseChargeStatus(JSON.stringify(data)).controls[0].end, null)
})
