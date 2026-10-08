import os

import gradio as gr
from dotenv import load_dotenv
load_dotenv()

from CSC311.recognizer import Recognizer
from CSC311.preprocessing import preprocess_frame, to_base64_jpeg
# Initialize one recognizer at startup, this will be reused across requests
recognizer = Recognizer()

# Gradio calls this with a numpy array when user uploads or captures an image
def recognize_image(image) -> tuple[str, str]:
    if image is None:
        return "", "No image provided."
    img, source_type = preprocess_frame(image, source_type="auto")
    b64 = to_base64_jpeg(img)

    result = recognizer._call_api(b64, source_type, label="<upload>")

    if not result.topics:
        return "No CSC311 topic detected.", result.explanation

    # Build output string
    lines = []
    for t in result.topics:
        conf = result.confidence.get(t.key, 0.0)
        lines.append(f"{t.label} = {conf:.0%} confidence")

    topics_str = "\n".join(lines)
    details = f"Explanation: {result.explanation}"
    if result.subtopics:
        details += f"\nSubtopics: {','.join(result.subtopics)}"

    return topics_str, details

# UI Layout
with gr.Blocks(title="EduTracker") as demo:
    gr.Markdown(
        """
        # Subject Recognizer
        Upload a photo or use your webcam to identify which topic is shown.
        Works with whiteboards, handwritten notes, and tablet drawings.
        """
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

            upload_btn = gr.Button("Recognize", variant="primary")
            upload_btn.click(
                fn=recognize_image,
                inputs=upload_input,
                outputs=[upload_topics, upload_details],
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

            webcam_btn = gr.Button("Recognize", variant="primary")
            webcam_btn.click(
                fn=recognize_image,
                inputs=webcam_input,
                outputs=[webcam_topics, webcam_details],
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

