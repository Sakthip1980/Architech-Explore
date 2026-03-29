# Learn Python — Build Hardware Simulators

A practical Python curriculum designed around the ArchSim codebase.
Every concept taught is directly used in the simulator's source code.

## How to Run a Lesson

```bash
python learn_python/lesson_01_variables_and_types.py
```

Run each lesson, read the code top-to-bottom, complete the exercise at the bottom,
then move to the next lesson.

---

## Curriculum Map

| Lesson | File | What You Learn | Where It Appears in ArchSim |
|--------|------|----------------|-----------------------------|
| 1 | `lesson_01_variables_and_types.py` | Variables, numbers, strings, f-strings, arithmetic | Every file |
| 2 | `lesson_02_lists_and_dicts.py` | Lists, dicts, loops, list of dicts | `configs/hardware_presets.py`, `configs/model_presets.py` |
| 3 | `lesson_03_functions.py` | def, parameters, return, default args | `simulator/models/*.py` — every calculation |
| 4 | `lesson_04_control_flow.py` | if/elif/else, for, while, break, list comprehension | `models/dram.py`, `models/npu.py`, bottleneck detection |
| 5 | `lesson_05_classes.py` | Classes, `__init__`, methods, inheritance, ABC | `simulator/base.py`, all hardware models |
| 6 | `lesson_06_dataclasses_and_enums.py` | `@dataclass`, `Enum`, `Optional`, type hints | `SimulationMetrics`, `DataflowMode`, `PrecisionMode` |
| 7 | `lesson_07_files_and_json.py` | File I/O, JSON read/write, CSV parsing | `simulator_api.py` state file, `workload.py` CSV import |
| 8 | `lesson_08_mini_simulator.py` | **Full mini simulator** combining all concepts | Mirrors `simulator/models/cache.py` + `systolic_array.py` |

---

## Learning Path

```
Lesson 1  →  Lesson 2  →  Lesson 3  →  Lesson 4
  (data)      (structure)  (functions)  (logic & loops)
                                             ↓
                              Lesson 5  ←  Lesson 4
                              (classes)
                                  ↓
                     Lesson 6        Lesson 7
                   (dataclass        (file I/O
                    & enum)           & JSON)
                          ↘         ↙
                          Lesson 8
                      (mini simulator)
```

---

## After Lesson 8

Once you complete all lessons, explore these real simulator files in order:

1. `simulator/base.py` — the abstract `Module` class (Lesson 5 + 6)
2. `simulator/models/dram.py` — a real hardware module
3. `simulator/models/cache.py` — multi-level cache logic
4. `simulator/models/workload.py` — CSV loading + GEMM maths
5. `simulator/models/systolic_array.py` — the most complex module
6. `server/simulator_api.py` — how the frontend calls the Python backend
