from dotenv import load_dotenv
from edutracker.recognizer import Recognizer

load_dotenv()

r = Recognizer()

# Get result from webcam
result = r.capture_and_recognize()
print(result)