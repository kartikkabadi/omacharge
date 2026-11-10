const test = require('node:test');
const assert = require('node:assert/strict');
const model = require('../ChargeModel.js');
function state() {
  return {version:'0.1.2',installed:true,error:'',conflicts:[],batteries:[{id:'BAT0'}],controls:[{
    id:'BAT0',driver:'dell',label:'BAT0',kind:'threshold',shared:false,stopValues:[60,80,100],startValues:[50,60,70,75,95],
    derived:'',gap:5,fullStart:95,end:80,start:75,careStop:80,fullStop:100,persisted:false,warning:'',saved:null
  }]};
}
test('accept the complete public protocol',()=>assert.equal(model.parse(JSON.stringify(state())).controls[0].end,80));
test('reject malformed nested controls before QML evaluates them',()=>{
  for(const mutate of [d=>delete d.stopValues,d=>d.startValues='oops',d=>d.fullStop=85,d=>d.end=true,d=>d.gap=-1,d=>d.warning={},d=>d.saved={end:80,start:false,source:'plugin'}]) {
    const data=state(); mutate(data.controls[0]); assert.throws(()=>model.parse(JSON.stringify(data)));
  }
});
test('reject duplicate identifiers and oversized arrays',()=>{
  const data=state(); data.controls.push(data.controls[0]); assert.throws(()=>model.parse(JSON.stringify(data)));
  const long=state(); long.controls[0].stopValues=Array(102).fill(80); assert.throws(()=>model.parse(JSON.stringify(long)));
});
test('bound the full process payload',()=>assert.throws(()=>model.parse(' '.repeat(131073))));
test('allow missing hardware presets explicitly as null',()=>{
  const data=state(); data.controls[0].careStop=null; data.controls[0].fullStop=null;
  assert.equal(model.parse(JSON.stringify(data)).controls[0].fullStop,null);
});
test('keep markup-shaped text as data for plain-text sinks',()=>{
  const data=state(); data.controls[0].label='<img src="https://example.invalid/tracker">';
  assert.equal(model.parse(JSON.stringify(data)).controls[0].label,data.controls[0].label);
});

const display = require('../Model.js');
test('bar and panel percentages use one integer display rule',()=>{
  assert.equal(display.displayPercentage(0.829183),82);
  assert.equal(display.displayPercentage(0.8),80);
  assert.equal(display.displayPercentage(0.29),29);
  for (const value of [null, undefined, NaN, Infinity, '0.8', -0.1, 1.1]) assert.equal(display.displayPercentage(value),null);
  assert.equal(display.displayPercentage(1),100);
});
test('explain an Apple percentage difference without changing either reading',()=>{
  const batteries=[{id:'macsmc-battery',capacity:80,status:'Not charging'}];
  assert.deepEqual(model.appleReadingDifference(batteries,{id:'macsmc-battery',driver:'apple'},82),{native:80,desktop:82});
  assert.equal(batteries[0].capacity,80);
});
test('do not compare an individual battery with a multi-battery desktop aggregate',()=>{
  const device={id:'BAT0',driver:'apple'};
  assert.equal(model.appleReadingDifference([{id:'BAT0',capacity:80},{id:'BAT1',capacity:50}],device,82),null);
  assert.equal(model.appleReadingDifference([{id:'BAT1',capacity:80}],device,82),null);
  assert.equal(model.appleReadingDifference([{id:'BAT0',capacity:80}],{id:'BAT0',driver:'dell'},82),null);
});
test('hide the comparison when readings agree or telemetry is unavailable',()=>{
  const device={id:'BAT0',driver:'apple'};
  assert.equal(model.appleReadingDifference([{id:'BAT0',capacity:80}],device,80),null);
  for (const capacity of [undefined,null,'80',true,101,-1])
    assert.equal(model.appleReadingDifference([{id:'BAT0',capacity}],device,82),null);
  assert.equal(model.appleReadingDifference([{id:'BAT0',capacity:80}],device,-1),null);
});
test('validate optional battery telemetry before explanatory text binds to it',()=>{
  for (const fields of [{capacity:'80'},{capacity:101},{capacity:true},{status:{}},{status:'x'.repeat(81)}]) {
    const data=state();Object.assign(data.batteries[0],fields);
    assert.throws(()=>model.parse(JSON.stringify(data)));
  }
});
