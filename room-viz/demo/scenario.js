/* Scripted walk-in scenario — the demo's 30 seconds (MASTER_PLAN §1, 0:15–0:45).
 * "Alexa, what's my day?" -> FULL card. MIL crosses the kitchen threshold ->
 * border shifts emerald->ember -> disclosure flips FULL->EXISTENCE.
 * Autoplays when index.html has ?autoplay=1 (used by headless frame captures).
 */
(function (global) {
  'use strict';

  function playWalkIn(bus) {
    var steps = [
      // Priya alone in the kitchen: private room, FULL disclosure.
      [400,  'earshot:presence',   { person: 'Priya', room: 'kitchen', confidence: 0.97 }],
      [700,  'earshot:disclosure', { room: 'kitchen', level: 'FULL', itemId: 'cal-prenatal',
                                     reasons: ['audience={Priya}', 'topic=calendar:medical'] }],
      [900,  'earshot:disclosure', { room: 'living', level: 'FULL' }],
      // "Alexa, what's my day?" — wake-word re-samples presence (P0-1), violet pulse.
      [2600, 'earshot:wakeword',    { ts: Date.now() }],
      // MIL walks in the front door, crosses the hall, crosses the kitchen threshold.
      [3400, 'earshot:presence',    { person: 'MIL', room: 'kitchen', confidence: 0.93 }],
      // Policy re-decides the moment she crosses: FULL -> EXISTENCE, ember border.
      [5600, 'earshot:disclosure',  { room: 'kitchen', level: 'EXISTENCE', itemId: 'cal-prenatal',
                                     reasons: ['audience={Priya,MIL}', 'deny-rule: clinic-in-front-of-Mom'] }],
      // Arjun settles in the living room — stays FULL (trusted).
      [7000, 'earshot:presence',    { person: 'Arjun', room: 'living', confidence: 0.88 }],
      [7400, 'earshot:disclosure',  { room: 'living', level: 'FULL' }]
    ];
    steps.forEach(function (s) {
      setTimeout(function () { bus.emit(s[1], s[2]); }, s[0]);
    });
  }

  global.playWalkIn = playWalkIn;
})(window);
