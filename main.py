import sys
from dotenv import load_dotenv
from edutracker.recognizer import Recognizer

load_dotenv()

# Optional course code, this can be left out if theres only one course
course = sys.argv[1] if len(sys.argv) > 1 else None

try:
    r = Recognizer(course=course)
except ValueError as e:
    sys.exit(f"Error: {e}")

# Get result from webcam
result = r.capture_and_recognize()
print(result)