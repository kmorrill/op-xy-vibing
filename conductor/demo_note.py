from conductor.midi_engine import Engine, VirtualSink


def main():
    doc = {
        "version": "opxyloop-1.0",
        "meta": {"tempo": 120, "ppq": 96, "stepsPerBar": 16},
        "tracks": [
            {
                "id": "t1",
                "name": "Test",
                "type": "sampler",
                "midiChannel": 0,
                "pattern": {
                    "lengthBars": 1,
                    "steps": [
                        {
                            "idx": 0,
                            "events": [
                                {"pitch": 60, "velocity": 110, "lengthSteps": 1}
                            ],
                        }
                    ],
                },
            }
        ],
    }

    sink = VirtualSink()
    eng = Engine(sink)
    eng.load(doc)
    eng.start()
    step_ticks = int((96 * 4) / 16)
    for t in range(0, step_ticks + 1):
        eng.on_tick(t)
    print("events:")
    for e in sink.events:
        print(e)


if __name__ == "__main__":
    main()

