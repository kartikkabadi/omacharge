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
