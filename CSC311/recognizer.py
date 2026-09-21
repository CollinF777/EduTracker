import json
import os
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from openai import OpenAI

from preprocessing import image_to_base64, preprocess_frame, to_base64_jpeg
from topics import TOPIC_MAP, TOPICS, Topic

# Makes a dataclass to hold our results
@dataclass
class RecognitionResult:
    image_path: str # could be file path or "<camera>" if live capture is being used
    topics: list[Topic]
    confidence: dict # dictonary will have the topic key and then a float value of 0-1
    explanation: str # a readable explanation of what was detected
    subtopics: list[str] # a list of specfic topics spotted, allowing us to see how the result was obtained
    source_type: str  # either whiteboard, paper, or raw
    raw_response: str ="" # full model response json for debugging purposes

    def __str__(self):
        if not self.topics:
            return f"[{self.image_path}] No topic detected.\n{self.explanation}"

        # Starts output with just the filename
        lines = [f"[{Path(self.image_path).name}]"]
        # Add one line for each detected topic alongside its confidence
        # This would look something like "- Karnaugh Map (K-Map) (97% Confidence)"
        for t in self.topics:
            # The 0.0 is meant to handle any keys with missing confidence
            conf = self.confidence.get(t.key, 0.0)
            # :.0% formats a float as a percantage with no decimal places i.e. 0.94 -> 94%
            lines.append(f"- {t.label} ({conf:.0%} Confidence)")
        # Always adds the explanation after topic list
        lines.append(f"\n Explanation: {self.explanation}")
        # Doesnt bother adding subtopics if none are found
        if self.subtopics:
            # What join is doing here is seperating each subtopic with a comma
            lines.append(f"\n Subtopics: {', '.join(self.subtopics)}")
        # Combines all lines into one string with newlines in between them
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "image_path": self.image_path,
            "topics": [{"key": t.key, "label": t.label} for t in self.topics],
            "confidence": self.confidence,
            "explanation": self.explanation,
            "subtopics": self.subtopics,
            "source_type": self.source_type,
        }

# Prompt for ai
def _build_system_prompt() -> str:
    """
    Build a block of text that lists every topic key and label
    This will get injected into the prompt so the model knows what topics there are
    This will make each line look something like: "kmap": "Karnaugh Map (K-Map)..."
    side note: does anybody know why this comment is gray instead of green like the other multi line comments
    I dropped description because I dont want to spend a ton of tokens everytime and the model should know these things anyways
    """
    topic_block = "\n".join(f' "{t.key}: "{t.label}"' for t in TOPICS)
    """
    Build a block of text that lists visual cues for each topic
    This tells the model what to look for in the image for each topic
    This will make each line look something like: kmap: Gray-code headers; Circled groups of cells; ...
    The join() combines the list of cues into a single semicolon-separated sentence
    For now this is going to be cut to save token usage but depending on the quality of response it can be added back in
    """
    # cues_block = "\n".join(f' {t.key}: {"; ".join(t.visual_cues)}' for t in TOPICS)
    # This is the ai prompt, if cues get added back in them add it below topic taxonomy
    return f"""You are an expert teaching assistant for CSC311 (Computer Organization and Architecture). 
    
    Your task is to look at the photo provided (whiteboard, handwritten paper, etc) and identify which CSC311
    topic(s) are visible. THe image may be noisy, at an angle, or partially legible - do your best
    
    === TOPIC TAXONOMY ===
    {topic_block}
    
    === OUTPUT FORMAT ===
    Respond ONLY with a single valid JSON object 0 no prose, no markdown fences:
    {{
        "topics": ["topic_key1", "topic_key2"],
        "confidence": {{"topic_key1": 0.92, "topic_key2": 0.75}},
        "explanation": "One or two sentences describing exactly what you see and why you assigned these topics.",
        "subtopics": ["specific concept A", "specific concept B"]
    }}
    
    Rules:
    - "topics" must be a list of keys from taxonomy above (empty list [] if nothing matches CSC311)
    - "confidence" values: 0.9+ = very clear, 0.7-0.9 = reasonable clear, 0.5-0.7 = partially visible/uncertain
    - "subtopics" are specific named concepts spotted (e.g. "De Morgan's Law", "D Flip-Flop", "Booths Algorithm", "ISZ instruction")
    - If the image is unreadable or clearly unrelated to CSC311, return topics: []
    - Do NOT include any text outside the JSON object
    """

# Subject recognizer using GPT-4o vision.
class Recognizer:
    def __init__(self, api_key: str | None = None, model: str="gpt-4o", preprocess: bool = True, source_type: str = "auto"):
        key = api_key or os.environ.get("OPENAPI_API_KEY")
        if not key:
            raise ValueError(
                "No OpenAI API key provided. Set OPENAI_API_KEY environment variable "
                "or pass api_key= to Recognizer()."
            )

        self._client = OpenAI(api_key=key)
        self._model = model
        self._preprocess = preprocess
        self._source_type = source_type
        self._system_prompt = _build_system_prompt()

    # Recognize topics from a single image file
    def recognize(self, image_path: str) -> RecognitionResult:
        path = str(image_path)
        if not Path(path).exists():
            raise FileNotFoundError(f"Image not found: {path}")

        b64, source_type = image_to_base64(path, preprocess_image=self._preprocess, source_type=self._source_type)
        return self._call_api(b64, source_type, label=path)

    # Recognize topics from mutiple images
    def recognize_batch(self, image_paths: list[str]) -> list[RecognitionResult]:
        results = []
        for path in image_paths:
            try:
                results.append(self.recognize(path))
            except Exception as e:
                # Return a failed result instead of crashing the whole thing
                results.append(RecognitionResult(
                    image_path=path,
                    topics=[],
                    confidence={},
                    explanation=f"Error during recognition: {e}",
                    subtopics=[],
                    source_type="unknown",
                    raw_response="",
                ))
        return results

    # Open live webcam, space to capture and recognize, Q to quit without capturing
    def capture_and_recognize(self, camera_index: int = 0) -> RecognitionResult | None:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            raise RuntimeError(
                f"Could not open {camera_index}. "
                "Check that your webcam is connected and not in use by another app."
            )

        print("Camera ready - press space to capture, q to quit.")

        captured_frame = None
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError("Failed to read from camera.")

                # Draw instructions on the live preview
                display = frame.copy()
                cv2.putText(
                    display,
                    "Space = capture | Q =  quit",
                    org=(10, 30),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                    fontScale=0.8,
                    color=(0, 255, 0),
                    thickness=2,
                    lineType=cv2.LINE_AA,
                )
                cv2.imshow("EduTracker - Live Preview", display)

                key = cv2.waitKey(1) & 0xFF
                if key == ord(" "):
                    captured_frame = frame
                    break

                elif key == ord("q") or key == 27: # Q or Escape
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()

        if captured_frame is None:
            print("No frame captured")
            return None

        print("Frame captured - recognizing...")
        img, source_type = preprocess_frame(
            captured_frame,
            source_type=self._source_type,
        )
        b64 = to_base64_jpeg(img)
        return self._call_api(b64, source_type, label="<camera>")

    # Send a base64 image to GPT-4o and return a RecognitionResult
    def _call_api(self, b64: str, source_type: str, label: str) -> RecognitionResult:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=512,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "high",
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Identify which CSC311 topic(s) are shown in this photo. "
                                "This may be a whiteboard, handwritten paper, or some other type of drawing"
                            ),
                        },
                    ],
                },
            ],
        )
        raw = response.choices[0].message.content.strip()
        return self._parse_response(raw, label, source_type)

    # Parse the models JSON response into a RecognitionResult
    def _parse_response(self, raw: str, path: str, source_type: str) -> RecognitionResult:
        text = raw
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                stripped = part.strip().lstrip("json").strip()
                if stripped.startswith("{"):
                    text = stripped
                    break

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return RecognitionResult(
                image_path=path,
                topics=[],
                confidence={},
                explanation=f"Model returned unparsable response: {raw[:200]}",
                subtopics=[],
                source_type=source_type,
                raw_response=raw,
            )

        topic_keys = data.get("topics", [])
        topics = [TOPIC_MAP[k] for k in topic_keys if k in TOPIC_MAP]
        confidence = {k: float(v) for k, v in data.get("confidence", {}).items()}
        explanation = data.get("explanation", "")
        subtopics = data.get("subtopics", [])

        return RecognitionResult(
            image_path=path,
            topics=topics,
            confidence=confidence,
            explanation=explanation,
            subtopics=subtopics,
            source_type=source_type,
            raw_response=raw,
        )
