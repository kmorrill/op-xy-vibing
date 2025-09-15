from __future__ import annotations

from typing import Dict, Any

from conductor.midi_engine import Engine, VirtualSink


def _make_doc(tr: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "version": "opxyloop-1.0",
        "meta": {"tempo": 120, "ppq": 96, "stepsPerBar": 16},
        "tracks": [
            {
                "id": "t1",
                "name": "T1",
                "type": "sampler",
                "midiChannel": 0,
                "pattern": {"lengthBars": 1, "steps": []},
                **tr,
            }
        ],
    }


def _filter_cc(events, ctrl: int, ch: int = 0):
    return [e for e in events if e[0] == "cc" and e[1] == ch and e[2] == ctrl]


def test_lfo_square_sync_quarter_note_basic():
    # Square @ 1/4 note; depth 20 (amp 10); offset 64; expect 54 then 74 within a bar
    sink = VirtualSink()
    eng = Engine(sink)
    doc = _make_doc({
        "lfos": [
            {"id": "a", "dest": "name:cutoff", "depth": 20, "rate": {"sync": "1/4"}, "shape": "square", "offset": 64}
        ]
    })
    eng.load(doc)
    eng.start()
    # bar ticks = ppq*4 = 96*4 = 384
    # quarter-note length = 384/4 = 96
    # sample two positions in bar
    eng.on_tick(0)
    eng.on_tick(60)
    eng.on_tick(120)
    vals = [v[3] for v in _filter_cc(sink.events, 32, 0)]
    assert 54 in vals and 74 in vals


def test_lfo_center_from_lane_when_present():
    # Lane holds 80; LFO offset 64 should be ignored for centering; square (+/- 10)
    sink = VirtualSink()
    eng = Engine(sink)
    doc = _make_doc({
        "ccLanes": [
            {"id": "x", "dest": "name:cutoff", "mode": "hold", "points": [{"t": {"bar": 0, "step": 0}, "v": 80}]}
        ],
        "lfos": [
            {"id": "lfo", "dest": "name:cutoff", "depth": 20, "rate": {"sync": "1/4"}, "shape": "square", "offset": 64}
        ],
    })
    eng.load(doc)
    eng.start()
    eng.on_tick(0)   # low half
    eng.on_tick(60)  # high half (tpc=96 -> toggle at 48)
    vals = [v[3] for v in _filter_cc(sink.events, 32, 0)]
    assert 70 in vals and 90 in vals  # centered around 80


def test_lfo_fade_ms_and_windows():
    # Validate window gating + fade using engine's lfo snapshot
    sink = VirtualSink(); eng = Engine(sink)
    step_ticks = int((96*4)/16)  # 24
    doc = _make_doc({
        "lfos": [{
            "id":"w","dest":"name:cutoff","depth":20,
            "rate":{"sync":"1/4"},"shape":"saw","offset":64,
            "fadeMs":100,
            "on":[{"from":{"bar":0,"step":8},"to":{"bar":0,"step":12}}]
        }]
    })
    eng.load(doc); eng.start()
    # Before window
    eng.on_tick(step_ticks*4); pre = [x for x in eng.get_lfo_snapshot() if x.get('lfoId')=='w'][0]
    # At window start
    eng.on_tick(step_ticks*8); start = [x for x in eng.get_lfo_snapshot() if x.get('lfoId')=='w'][0]
    # Later within window
    eng.on_tick(step_ticks*10); mid = [x for x in eng.get_lfo_snapshot() if x.get('lfoId')=='w'][0]
    # After window
    eng.on_tick(step_ticks*13); post = [x for x in eng.get_lfo_snapshot() if x.get('lfoId')=='w'][0]
    assert not pre['active'] and not post['active']
    assert start['active'] and mid['active']
    assert abs(start['value']-start['center']) <= abs(mid['value']-mid['center'])


def test_lfo_hz_equivalence_with_sync_quarter():
    # 2 Hz at 120bpm, ppq=96 -> ticks/sec=192 -> tpc=96 which equals 1/4 note
    def run_with_rate(rate_obj):
        sink = VirtualSink(); eng = Engine(sink)
        doc = _make_doc({
            "lfos": [
                {"id": "h", "dest": "name:cutoff", "depth": 20, "rate": rate_obj, "shape": "square", "offset": 64}
            ]
        })
        eng.load(doc); eng.start();
        for t in (0, 60, 120, 180, 240):
            eng.on_tick(t)
        return [v[3] for v in _filter_cc(sink.events, 32, 0)]

    a = run_with_rate({"sync": "1/4"})
    b = run_with_rate({"hz": 2})
    # Both sequences should contain the same unique set of values
    assert set(a) == set(b)


def test_lfo_triangle_sync_half_cycle_values():
    # Triangle @ 1/2 note; depth 20 (amp 10); offset 64
    # Expect: start 54, quarter 64, half 74
    sink = VirtualSink(); eng = Engine(sink)
    doc = _make_doc({
        "lfos": [
            {"id":"tri","dest":"name:cutoff","depth":20,"rate":{"sync":"1/2"},"shape":"triangle","offset":64}
        ]
    })
    eng.load(doc); eng.start()
    # bar_ticks = 384; 1/2 -> tpc=192
    eng.on_tick(0)      # start -> -1 -> 54
    eng.on_tick(48)     # quarter -> ~64
    eng.on_tick(96)     # half -> +1 -> 74
    vals = [e[3] for e in _filter_cc(sink.events, 32, 0)]
    assert 54 in vals and 74 in vals and any(abs(v-64)<=1 for v in vals)


def test_lfo_ramp_and_saw_directions():
    # ramp (rise): start -1 (54), mid 0 (~64), end +1 (74)
    # saw (fall): start +1 (74), end -1 (54)
    def run(shape):
        s = VirtualSink(); eng = Engine(s)
        doc = _make_doc({"lfos":[{"id":shape,"dest":"name:cutoff","depth":20,"rate":{"sync":"1/2"},"shape":shape,"offset":64}]})
        eng.load(doc); eng.start();
        # tpc=192
        ticks = [0, 96, 192-1]
        for t in ticks: eng.on_tick(t)
        return [e[3] for e in _filter_cc(s.events, 32, 0)]
    vals_ramp = run("ramp")
    vals_saw  = run("saw")
    assert 54 in vals_ramp and 74 in vals_ramp
    assert 54 in vals_saw and 74 in vals_saw
    # ramp should include center-ish value near 64; saw may not include exact center in these probes
    assert any(abs(v-64)<=1 for v in vals_ramp)


def test_lfo_triplet_sync_1_8T_cycle_length():
    # 1/8T -> 12 cycles per bar -> tpc = bar_ticks/12 = 32
    sink = VirtualSink(); eng = Engine(sink)
    doc = _make_doc({
        "lfos": [{"id":"trip","dest":"name:cutoff","depth":20,"rate":{"sync":"1/8T"},"shape":"square","offset":64}]
    })
    eng.load(doc); eng.start()
    # Expect alternation every 16 ticks (half cycle)
    eng.on_tick(0)
    eng.on_tick(16)
    eng.on_tick(32)
    vals = [e[3] for e in _filter_cc(sink.events, 32, 0)]
    # Should contain both extremes 54 and 74
    assert 54 in vals and 74 in vals


def test_samplehold_changes_on_wrap_only():
    # 1/8T -> tpc = 32; S&H should hold within a cycle and change at wrap
    sink = VirtualSink(); eng = Engine(sink)
    doc = _make_doc({
        "lfos": [{"id":"sh","dest":"name:cutoff","depth":20,"rate":{"sync":"1/8T"},"shape":"samplehold","offset":64}]
    })
    eng.load(doc); eng.start()
    # Tick 0 and 16 (within same cycle) -> same value; tick 32 -> new value
    for t in (0, 16):
        eng.on_tick(t)
        v = [e[3] for e in _filter_cc(sink.events, 32, 0)][-1]
        if t == 0: v0 = v
        else: v1 = v
    eng.on_tick(32)
    v2 = [e[3] for e in _filter_cc(sink.events, 32, 0)][-1]
    assert v0 == v1 and v2 != v1


def test_lane_range_clamp_post_merge():
    # ccLane holds 64 with range [60,68]; square depth 40 (amp 20) should be clamped to 60..68
    sink = VirtualSink(); eng = Engine(sink)
    doc = _make_doc({
        "ccLanes": [{"id":"base","dest":"name:cutoff","mode":"hold","range":[60,68],"points":[{"t":{"bar":0,"step":0},"v":64}]}],
        "lfos": [{"id":"sq","dest":"name:cutoff","depth":40,"rate":{"sync":"1/4"},"shape":"square","offset":64}]
    })
    eng.load(doc); eng.start()
    # bar_ticks=384, 1/4 -> tpc=96; sample values at extremes
    eng.on_tick(0)   # low extreme would be 44 -> clamp to 60
    eng.on_tick(48)  # other half -> 84 -> clamp to 68
    vals = [e[3] for e in _filter_cc(sink.events, 32, 0)]
    assert 60 in vals and 68 in vals


def test_phase_offset_shifts_cycle():
    # Sine 1/4 with phase 0.5: 180° shifted value at the same sample position
    def run(ph, t):
        s = VirtualSink(); eng = Engine(s)
        doc = _make_doc({"lfos":[{"id":"ph","dest":"name:cutoff","depth":20,"rate":{"sync":"1/4"},"shape":"sine","offset":64,"phase":ph}]})
        eng.load(doc); eng.start(); eng.on_tick(t)
        return [e[3] for e in _filter_cc(s.events, 32, 0)][-1]
    v0 = run(0.0, 24)  # sample at quarter of cycle (tpc=96 -> 24)
    v1 = run(0.5, 24)
    assert v0 != v1
