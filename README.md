# EduTracker

EduTracker looks at a photo of a whiteboard, handwritten notes, or a tablet drawing and tells you which course topic it covers. It can also transcribe the handwriting into a Word document, with any spots it is unsure about highlighted in yellow.

It uses GPT-4o vision. You define each course in a small YAML file, so adding a new course doesn't require any code changes.

## Features

- **Topic recognition**: matches a photo to one or more topics from a course, with a confidence score, a short explanation, and specific subtopics spotted
- **Handwriting transcription**: exports the notes to a `.docx` file, with uncertain spots highlighted
- **Double-check mode**: an optional extra proofreading pass that catches skipped or duplicated lines (slower, one more API call)
- **Multiple courses**: pick a course per photo; every course is a YAML file in `courses/`
- **"No course" mode**: transcription only, no topic recognition
- **Image preprocessing**: whiteboard/paper enhancement, deskewing, and resizing before the image is sent to the API
- **Three ways to use it**: web app, command line, or live webcam capture
- **Evaluation suite**: measures topic precision/recall and transcription error rates (see [Evaluation](#evaluation))

## Setup

Requires Python 3 and an OpenAI API key.

```bash
git clone https://github.com/CollinF777/EduTracker.git
cd EduTracker
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your-key-here
```

Optional environment variables:

| Variable | Purpose | Default |
|---|---|---|
| `PORT` | Port for the web app | `7860` |
| `EDUTRACKER_COURSES_DIR` | Folder to load course YAML files from | `./courses` |

> Depending on your system you may need `python3` or `py` instead of `python` in the commands below.

## Usage

### Web app

```bash
python app.py
```

Open http://localhost:7860, choose a course, then upload an image or use your webcam. Tick **Also transcribe** to get a Word document, and **Double-check** for the extra proofreading pass. Picking "No course (transcribe only)" skips topic recognition and always transcribes.

### Command line

```bash
python cli.py photo.jpg --course CSC311     # course can be left out if there is only one
python cli.py --list-courses
python cli.py whiteboard.png --source whiteboard
python cli.py img1.jpg img2.png img3.jpg    # several images at once
python cli.py photo.jpg --no-preprocess     # faster, worse on noisy photos
python cli.py photo.jpg --json              # machine-readable output
```

| Option | Description |
|---|---|
| `--course`, `-c` | Course code (see `--list-courses`) |
| `--list-courses` | Show available courses and exit |
| `--source` | `auto` (default), `whiteboard`, or `paper` |
| `--no-preprocess` | Skip image enhancement |
| `--model` | OpenAI model to use (default `gpt-4o`) |
| `--json` | Output results as JSON |

### Webcam

```bash
python main.py [COURSE]
```

Captures a frame from your webcam and prints the recognized topics.

### Python

```python
from edutracker.recognizer import Recognizer

r = Recognizer(course="CSC311")
result = r.recognize("photo.jpg")
print(result)

# Recognition plus transcription
result, transcription = r.transcribe("photo.jpg")
```

## Adding a course

1. Copy `courses/_template.yaml` to `courses/<CODE>.yaml`
2. Fill in the course code, name, and topics. Each topic has a `key`, a `label`, and optionally a `description` and `visual_cues` describing what it looks like on a whiteboard
3. Restart the app or CLI

Files starting with `_` are ignored. The course name goes into the AI prompt, so keep it accurate.

Included courses: `CSC120`, `CSC311` (Computer Organization and Architecture), and `MTH111`.

## Project structure

```
app.py               Gradio web app
cli.py               Command line interface
main.py              Webcam capture
courses/             One YAML file per course
edutracker/
  recognizer.py      Topic recognition and transcription via the OpenAI API
  courses.py         Course loading
  transcription.py   Transcription prompts and parsing
  preprocessing.py   Image enhancement, deskewing, resizing
  docx_export.py     Word document export
eval/                Evaluation scripts and labeled dataset
eval_results_nopre/  Saved evaluation results
```

## Evaluation

The `eval/` folder holds 30 labeled photos (10 each for CSC120, CSC311, and MTH111) with typed ground-truth transcripts. The evaluation tests whether giving the model course context improves transcription (character error rate) and how well topics are recognized. See [`eval/README.md`](eval/README.md) for the dataset format and how to type transcripts.

```bash
python -m eval.evaluate eval/dataset.csv
```

Raw results are saved so an interrupted run can be resumed by running the same command again. Use `--score-only` to re-score saved results without making API calls.

Results from the saved run (`eval_results_nopre/`, gpt-4o, preprocessing off):

| Metric | Result |
|---|---|
| Topic precision | 72.9% |
| Topic recall | 92.1% |
| Topic F1 | 81.4% |
| Exact topic-set match | 63.3% |
| Transcription CER (no context) | 24.8% |

Transcription error varies a lot by course: CER is about 5-7% for CSC120 and MTH111 but about 40% for CSC311, which is full of circuit diagrams and Boolean notation. Course context did not measurably lower CER in this run; the confidence intervals include zero.

## Notes

- Every recognition or transcription call sends the image to OpenAI, so it uses your API credits and needs an internet connection
