# EduTracker evaluation (30 images)

Model(s): gpt-4o. Error rates are pooled (total edits / total reference length).

## Topic recognition

| Group | n | Precision | Recall | F1 | Exact set match |
|---|---|---|---|---|---|
| All | 30 | 72.9% | 92.1% | 81.4% | 63.3% |
| quality: fair | 12 | 61.9% | 86.7% | 72.2% | 58.3% |
| quality: good | 17 | 80.0% | 100.0% | 88.9% | 70.6% |
| quality: poor | 1 | 100.0% | 66.7% | 80.0% | 0.0% |
| course: CSC120 | 10 | 52.6% | 100.0% | 69.0% | 40.0% |
| course: CSC311 | 10 | 88.9% | 88.9% | 88.9% | 70.0% |
| course: MTH111 | 10 | 81.8% | 90.0% | 85.7% | 80.0% |

## Transcription by context level

| Group | Context | n | CER | WER | Flags/img |
|---|---|---|---|---|---|
| All | full | 30 | 25.6% | 47.5% | 0.0 |
| All | course | 30 | 25.5% | 47.2% | 0.0 |
| All | none | 30 | 24.8% | 44.8% | 0.0 |
| quality: fair | full | 12 | 20.9% | 44.2% | 0.0 |
| quality: fair | course | 12 | 20.7% | 43.9% | 0.0 |
| quality: fair | none | 12 | 20.1% | 42.4% | 0.0 |
| quality: good | full | 17 | 25.9% | 49.1% | 0.0 |
| quality: good | course | 17 | 25.0% | 48.1% | 0.0 |
| quality: good | none | 17 | 23.8% | 44.1% | 0.0 |
| quality: poor | full | 1 | 38.5% | 52.2% | 0.0 |
| quality: poor | course | 1 | 42.2% | 55.7% | 0.0 |
| quality: poor | none | 1 | 43.6% | 56.5% | 0.0 |
| course: CSC120 | full | 10 | 6.4% | 40.7% | 0.0 |
| course: CSC120 | course | 10 | 6.9% | 42.1% | 0.0 |
| course: CSC120 | none | 10 | 6.6% | 41.6% | 0.0 |
| course: CSC311 | full | 10 | 41.9% | 58.8% | 0.0 |
| course: CSC311 | course | 10 | 40.8% | 57.0% | 0.0 |
| course: CSC311 | none | 10 | 40.3% | 53.6% | 0.0 |
| course: MTH111 | full | 10 | 5.0% | 25.0% | 0.0 |
| course: MTH111 | course | 10 | 6.4% | 27.3% | 0.0 |
| course: MTH111 | none | 10 | 5.3% | 26.5% | 0.0 |

## Does context help? (CER difference vs. no context, negative = better)

| Context | n paired | CER difference | 95% bootstrap CI |
|---|---|---|---|
| full | 30 | +0.78 pp | [-1.04, +2.56] pp |
| course | 30 | +0.68 pp | [-0.25, +1.74] pp |
