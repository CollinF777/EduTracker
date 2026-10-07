'''
Okay this is just the command line interface and theres a few ways to use it

python cli.py photo.jpg
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

from CSC311.recognizer import Recognizer

def main():
    parser = argparse.ArgumentParser(
        description="Identify CSC311 topics in whiteboard/handwritten photos."
    )
    parser.add_argument(
        "images",
        nargs="+",
        metavar="IMAGE",
        help="Path(s) to image file(s) to recognize",
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

    try:
        recognizer = Recognizer(
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