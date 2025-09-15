PY := python3

.PHONY: validate validate-fixtures hash-fixtures test demo-note

validate:
	@$(PY) -m conductor.validator $(FILE)

validate-fixtures:
	@set -e; \
	for f in conductor/tests/fixtures/*.json; do \
		echo "==> $$f"; \
		$(PY) -m conductor.validator $$f --print-hash || exit $$?; \
	done

canonicalize-fixtures:
	@set -e; \
	for f in conductor/tests/fixtures/*.json; do \
		echo "==> canon $$f"; \
		$(PY) -m conductor.validator $$f --write; \
	done

.PHONY: clock-smoke
clock-smoke:
	@$(PY) -m conductor.clock_smoke --bpm 120 --seconds 5

test:
	@$(PY) -m unittest discover -s conductor/tests -p "test_*.py" -v

demo-note:
	@$(PY) -m conductor.demo_note

.PHONY: play-internal play-external
play-internal:
	@$(PY) -m conductor.play_local $(LOOP) --mode internal --bpm $(BPM) --port "$(PORT)"

play-external:
	@$(PY) -m conductor.play_local $(LOOP) --mode external --port "$(PORT)"

.PHONY: conductor-run
conductor-run:
	@$(PY) -m conductor.conductor_server --loop $(LOOP) --port "$(PORT)" --bpm $(BPM) --ws-host 127.0.0.1 --ws-port 8765

.PHONY: ui-serve
ui-serve:
	@cd ui && $(PY) -m http.server 8080 --bind 127.0.0.1

.PHONY: ws-tempo ws-patch-vel
ws-tempo:
	@$(PY) tools/wsctl.py --url ws://127.0.0.1:8765 tempo --bpm $(BPM)
ws-patch-vel:
	@$(PY) tools/wsctl.py --url ws://127.0.0.1:8765 patch-vel --velocity $(VEL) $(APPLYNOW)

.PHONY: play-cc-lfo-internal
play-cc-lfo-internal:
	@$(PY) -m conductor.play_local conductor/tests/fixtures/loop-cc-lfo.json --mode internal --bpm $(BPM) --port "$(PORT)"

.PHONY: play-cc-lfo-ch0
play-cc-lfo-ch0:
	@$(PY) -m conductor.play_local conductor/tests/fixtures/loop-cc-lfo-ch0.json --mode internal --bpm $(BPM) --port "$(PORT)" --metrics $(METRICS)

.PHONY: play-vel-ch0
play-vel-ch0:
	@$(PY) -m conductor.play_local conductor/tests/fixtures/loop-vel-ch0.json --mode internal --bpm $(BPM) --port "$(PORT)" --loops $(LOOPS)

.PHONY: panic kill-procs kill-ws-port
panic:
	@$(PY) -c "from conductor.midi_out import open_mido_output, MidoSink; out=open_mido_output('$(PORT)'); MidoSink(out).panic(); print('panic sent (CC64/120/123)')" || true

kill-procs:
	@pkill -f "conductor.conductor_server" || true; \
	pkill -f "conductor.play_local" || true; \
	pkill -f "tools/wsctl.py" || true; \
	printf "done\n"

kill-ws-port:
	@pids=$$(lsof -t -iTCP:8765 -sTCP:LISTEN 2>/dev/null || true); if [ -n "$$pids" ]; then echo "killing WS PIDs: $$pids"; kill $$pids || true; sleep 1; kill -9 $$pids || true; else echo "no WS listener on 8765"; fi
.PHONY: play-vel-shaker
play-vel-shaker:
	@$(PY) -m conductor.play_local conductor/tests/fixtures/loop-vel-shaker.json --mode internal --bpm $(BPM) --port "$(PORT)" --loops $(LOOPS)

.PHONY: play-vel-ab-ch0
play-vel-ab-ch0:
	@$(PY) -m conductor.play_local conductor/tests/fixtures/loop-vel-ab-ch0.json --mode internal --bpm $(BPM) --port "$(PORT)" --loops $(LOOPS)

.PHONY: play-vel-ab-ch5
play-vel-ab-ch5:
	@$(PY) -m conductor.play_local conductor/tests/fixtures/loop-vel-ab-ch4.json --mode internal --bpm $(BPM) --port "$(PORT)" --loops $(LOOPS)

.PHONY: play-vel-ab-ch1-d3
play-vel-ab-ch1-d3:
	@$(PY) -m conductor.play_local conductor/tests/fixtures/loop-vel-ab-ch1-d3.json --mode internal --bpm $(BPM) --port "$(PORT)" --loops $(LOOPS)

.PHONY: play-vel-alt-ch1-d3
play-vel-alt-ch1-d3:
	@$(PY) -m conductor.play_local conductor/tests/fixtures/loop-vel-alt-ch1-d3.json --mode internal --bpm $(BPM) --port "$(PORT)" --loops $(LOOPS)
