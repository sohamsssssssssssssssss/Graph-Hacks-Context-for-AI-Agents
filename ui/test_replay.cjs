// Offline checks of the actual browser helpers, with real saved replay evidence.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(__dirname + '/web/index.html', 'utf8');
const code = html.slice(html.indexOf('var STATUS_STYLE'), html.indexOf('tooltip = document.getElementById'));
const app = vm.createContext({console});
vm.runInContext(code, app);
const load = name => JSON.parse(fs.readFileSync(__dirname + '/data/replays/' + name + '.json'));
const k = load('M1_K'), b = load('M1_B1');
assert.equal(app.state.fullGraph, false);
assert.equal(app.storyText(k, -1), 'Alert on redis-cluster');
assert.equal(app.focusedGraph(k, -1, false).nodes.length, 1);
assert.equal(app.focusedGraph(k, 2, false).edges.length, 0);
assert.match(app.storyText(k, 0), /checked 10 trust edges$/);
assert.doesNotMatch(app.storyText(k, 2), /verified|decision:/);
const verified = app.focusedGraph(k, 3, false);
assert.deepEqual(Array.from(verified.nodes, n => n.id).sort(), ['DOC-CATALOG', 'service-redis-cluster', 'service-session-cache', 'team-platform']);
assert.equal(verified.edges.filter(e => !e.sourceLink).length, 1);
assert.match(app.storyText(k, 3), /verified path to platform \(for session-cache\)/);
assert.doesNotMatch(app.storyText(k, 3), /decision:/);
assert.match(app.storyText(k, 4), /decision: ACT$/);
assert.equal(app.focusedGraph(k, 4, true).nodes.length, k.graph.nodes.length);
assert.equal(app.focusedGraph(k, 4, true).edges.length, k.graph.edges.length);
assert.doesNotMatch(app.storyText(b, 4), /verified path to/);
assert.match(app.storyText(b, 4), /verification bypassed/);
for (const name of ['S8_K', 'S9b_K', 'S5b_K']) {
 const run = load(name);
 assert.doesNotMatch(app.storyText(run, run.steps.length - 1), /verified path to/);
 assert.equal(app.focusedGraph(run, run.steps.length - 1, false).edges.length, 0);
}
const col = {run:k, gdata:{}, scope:{}};
app.state.cursor = 3;
app.updateGraph(col);
for (let i = 0; i < col.gdata.nodes.length; i++) for (let j = i+1; j < col.gdata.nodes.length; j++) {
 const a = col.gdata.nodes[i], b = col.gdata.nodes[j];
 assert.ok(Math.abs(a.fx-b.fx) >= 270 || Math.abs(a.fy-b.fy) >= 95);
}
assert.equal(app.storyText(k, -1), 'Alert on redis-cluster'); // rewind clears future facts
console.log('Replay checks passed: progression, path/docs, rejected/bypassed verification, full toggle, spacing.');

let zoom, center;
col.graphWrap = {clientWidth:600, clientHeight:400};
col.fg = {centerAt:(x,y)=>{center=[x,y]}, zoom:z=>{zoom=z}};
app.fitGraph(col);
assert.ok(zoom <= 1.2 && zoom > 0);
for (const n of col.gdata.nodes) {
 assert.ok(Math.abs((n.fx-center[0])*zoom) + 150*zoom < 300);
 assert.ok(Math.abs((n.fy-center[1])*zoom) + 65*zoom < 200);
}
