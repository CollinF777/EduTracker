'''
Okay this is just the command line interface and theres a few ways to use it

python cli.py photo.jpg -- course CSC311       (course can be left out if theres only one)
python cli.py --list-courses
python cli.py whiteboard.png --source whiteboard
python cli.py img1.jpg img2.png img3.jpg
python cli.py photo.jpg --no-preprocess
python cli.py photo.jpg --json                  this one just makes it machine readable

For reference, if this doesnt work you might have to do something
besides python in the front like python3, py, or something else
'''
import argparse
import json
import sys
from dotenv import load_dotenv

load_dotenv()

from edutracker.courses import load_courses
from edutracker.recognizer import Recognizer

def main():
    parser = argparse.ArgumentParser(
        description="Identify course topics in whiteboard/handwritten photos."
    )
    parser.add_argument(
        "images",
        nargs="+",
        metavar="IMAGE",
        help="Path(s) to image file(s) to recognize",
    )
    parser.add_argument(
        "--course",
        "-c",
        default=None,
        help="Course code to use, e.g. CSC311 (see --list-courses)",
    )
    parser.add_argument(
        "--list-courses",
        action="store_true",
        help="Show the available courses and exit",
    )
    parser.add_argument(
        "--source",
        choices=["auto", "whiteboard", "paper"],
        default="auto",
        help="Source type hint (default: auto-detect)",
    )
    parser.add_argument(
        "--no-preprocess",
        action="store_true",
        help="Skip image enchancement to make it faster but with a worse result on noisy photos).",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="OpenAI model to use (default: gpt-4o)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    if args.list_courses:
        for course in load_courses().values():
            print(course.label)
        return
    if not args.images:
        parser.error("at least one image is required")

    try:
        recognizer = Recognizer(
            course=args.course,
            model=args.model,
            preprocess=not args.no_preprocess,
            source_type=args.source,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if len(args.images) == 1:
        result = recognizer.recognize(args.images[0])
        if args.json_output:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(result)
    else:
        results = recognizer.recognize_batch(args.images)
        if args.json_output:
            print(json.dumps([r.to_dict() for r in results], indent=2))
        else:
            for r in results:
                print(r)
                print()

if __name__ == "__main__":
    main()