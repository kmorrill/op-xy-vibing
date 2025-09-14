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

.PHONY: ws-play ws-stop ws-continue ws-tempo ws-patch-vel
ws-play:
	@$(PY) tools/wsctl.py --url ws://127.0.0.1:8765 play
ws-stop:
	@$(PY) tools/wsctl.py --url ws://127.0.0.1:8765 stop
ws-continue:
	@$(PY) tools/wsctl.py --url ws://127.0.0.1:8765 continue
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
