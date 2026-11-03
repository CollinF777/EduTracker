import os
import tempfile

import gradio as gr
from dotenv import load_dotenv
load_dotenv()

from edutracker.courses import load_courses
from edutracker.recognizer import Recognizer
from edutracker.docx_export import docx_path_for, save_docx

COURSES = load_courses()
# Initialize a recognizer for each course on startup which will be used across requests
RECOGNIZERS = {code: Recognizer(course=course) for code, course in COURSES.items()}

# Gradio calls this with a numpy array when user uploads or captures an image
def recognize_image(image, course_code, transcribe=False) -> tuple[str, str, str | None]:
    if image is None:
        return "", "No image provided.", None
    if course_code not in RECOGNIZERS:
        return "", "Please select a course first", None
    recognizer = RECOGNIZERS[course_code]

    transcription = None
    if transcribe:
        result, transcription = recognizer.transcribe_frame(image, label="<upload>")
    else:
        result = recognizer.recognize_frame(image, label="<upload>")

    if not result.topics:
        topics_str = f"No {course_code} topic detected."
        details = result.explanation

    else:
        # Build output string
        lines = []
        for t in result.topics:
            conf = result.confidence.get(t.key, 0.0)
            lines.append(f"{t.label} = {conf:.0%} confidence")

        topics_str = "\n".join(lines)
        details = f"Explanation: {result.explanation}"
        if result.subtopics:
            details += f"\nSubtopics: {','.join(result.subtopics)}"

    # Gradio needs a real file on disk to offer as a download
    docx_file = None
    if transcription is not None:
        docx_file = str(save_docx(
            transcription,
            docx_path_for("<upload>", tempfile.mkdtemp()),
            course=recognizer.course,
            result=result,
        ))
        details += "\n\nTranscription saved, download it below."
        if transcription.uncertain_count:
            details += f" {transcription.uncertain_count} uncertain spot(s) are highlighted in yellow"

    return topics_str, details, docx_file

# UI Layout
with gr.Blocks(title="EduTracker") as demo:
    gr.Markdown(
        """
        # Subject Recognizer
        Upload a photo or use your webcam to identify which topic is shown.
        Works with whiteboards, handwritten notes, and tablet drawings.
        """
    )

    # Shared by both tabs
    course_picker = gr.Dropdown(
        choices=[(c.label, code) for code, c in COURSES.items()],
        value=next(iter(COURSES)),
        label="Course",
        interactive=True,
    )

    transcribe_box = gr.Checkbox(
        label="Also transcribe the handwriting into Word document (note: this will take longer)",
        value=False,
    )

    with gr.Tabs():
        # Upload tab
        with gr.Tab("Upload Image"):
            with gr.Row():
                upload_input = gr.Image(
                    label="Upload Image",
                    type="numpy", # convert image to numpy array
                    sources=["upload"] # Upload only on this tab
                )
                with gr.Column():
                    upload_topics=gr.Markdown(label="Detected Topics")
                    upload_details=gr.Markdown(label="Details")

            upload_file = gr.File(label="Word document")
            upload_btn = gr.Button("Recognize", variant="primary")
            upload_btn.click(
                fn=recognize_image,
                inputs=[upload_input, course_picker, transcribe_box],
                outputs=[upload_topics, upload_details, upload_file],
            )

        with gr.Tab("Use Webcam"):
            with gr.Row():
                webcam_input = gr.Image(
                    label="Webcam",
                    type="numpy",
                    sources=["webcam"] ,
                )
                with gr.Column():
                    webcam_topics = gr.Markdown(label="Detected Topics")
                    webcam_details = gr.Markdown(label="Details")

            webcam_file = gr.File(label="Word document")
            webcam_btn = gr.Button("Recognize", variant="primary")
            webcam_btn.click(
                fn=recognize_image,
                inputs=[webcam_input, course_picker, transcribe_box],
                outputs=[webcam_topics, webcam_details, webcam_file],
            )

    gr.Markdown(
        """
        Powered by GPT-4o vision
        """
    )

if __name__ == "__main__":
    # If theres no port set go to local 7860
    port = int(os.environ.get("PORT", 7860))
    demo.launch(
        server_name="0.0.0.0", # listen on all interfaces
        server_port=port,
        share=False, # If you set it to true then you can get a temp public URL
        theme=gr.themes.Soft(),
    )

