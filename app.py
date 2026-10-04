import streamlit as st
import pytesseract
from PIL import Image, ImageDraw, ImageFont
import cv2
import tempfile
import os
import shutil
import textwrap
from huggingface_hub import InferenceClient


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="LectureLens",
    page_icon="🎓",
    layout="wide"
)


# =========================================================
# TESSERACT CONFIGURATION
# =========================================================

# Windows
windows_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if os.path.exists(windows_tesseract):
    pytesseract.pytesseract.tesseract_cmd = windows_tesseract

# Linux / Streamlit Cloud
elif shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")


# =========================================================
# CUSTOM STYLING
# =========================================================

st.markdown("""
<style>

.main-title {
    font-size: 42px;
    font-weight: 700;
    text-align: center;
    margin-bottom: 5px;
}

.subtitle {
    text-align: center;
    font-size: 18px;
    margin-bottom: 30px;
}

.result-box {
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #dddddd;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# TITLE
# =========================================================

st.markdown(
    '<div class="main-title">🎓 LectureLens</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Turn lectures and documents into smart revision notes'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header("⚙️ Settings")

    frame_interval = st.slider(
        "Video frame interval (seconds)",
        min_value=2,
        max_value=10,
        value=4
    )

    st.info(
        "For a faster demo, use a short lecture video "
        "of around 1–5 minutes."
    )


# =========================================================
# FILE UPLOAD
# =========================================================

uploaded_file = st.file_uploader(
    "📤 Upload an image or lecture video",
    type=[
        "png",
        "jpg",
        "jpeg",
        "webp",
        "mp4",
        "mov",
        "avi"
    ]
)


# =========================================================
# OCR IMAGE PREPROCESSING
# =========================================================

def preprocess_image(image):

    image = image.convert("RGB")

    # Convert PIL image to OpenCV format
    img = cv2.cvtColor(
        __import__("numpy").array(image),
        cv2.COLOR_RGB2BGR
    )

    # Grayscale
    gray = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2GRAY
    )

    # Resize for better OCR
    gray = cv2.resize(
        gray,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC
    )

    # Threshold
    _, threshold = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return Image.fromarray(threshold)


# =========================================================
# OCR IMAGE
# =========================================================

def extract_text_from_image(image):

    processed = preprocess_image(image)

    text = pytesseract.image_to_string(
        processed,
        config="--psm 6"
    )

    return text.strip()


# =========================================================
# VIDEO OCR
# =========================================================

def extract_text_from_video(video_path, interval):

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)

    if fps <= 0:
        fps = 30

    frame_count = 0
    next_capture = 0

    results = []

    while True:

        success, frame = cap.read()

        if not success:
            break

        current_time = frame_count / fps

        if current_time >= next_capture:

            frame_rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            image = Image.fromarray(frame_rgb)

            text = extract_text_from_image(image)

            if text:

                results.append({
                    "time": current_time,
                    "text": text
                })

            next_capture += interval

        frame_count += 1

    cap.release()

    return results


# =========================================================
# REMOVE DUPLICATE OCR TEXT
# =========================================================

def remove_duplicates(results):

    cleaned = []

    previous_text = ""

    for item in results:

        current = " ".join(
            item["text"].split()
        )

        previous = " ".join(
            previous_text.split()
        )

        if not current:
            continue

        # Skip exact repeated text
        if current.lower() == previous.lower():
            continue

        cleaned.append({
            "time": item["time"],
            "text": current
        })

        previous_text = current

    return cleaned


# =========================================================
# AI SUMMARY
# =========================================================

def generate_summary(text):

    token = st.secrets.get(
        "HF_TOKEN",
        os.getenv("HF_TOKEN", "")
    )

    if not token:

        st.error(
            "HF_TOKEN is missing. Add it in Streamlit Secrets."
        )

        return None

    client = InferenceClient(
        api_key=token
    )

    prompt = f"""
You are LectureLens, an educational note-making assistant.

Analyze the following OCR-extracted lecture/document text.

Create concise and accurate study notes.

Return exactly these sections:

TITLE:
A suitable topic title.

SUMMARY:
A short 3-5 sentence explanation.

KEY POINTS:
Give 4-6 important bullet points.

KEYWORDS:
Give 5-8 important keywords.

QUICK REVISION:
Give a very short exam-oriented revision paragraph.

Do not invent information that is not present in the source text.

SOURCE TEXT:
{text[:15000]}
"""

    try:

        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an accurate educational "
                        "summarization assistant."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=900,
            temperature=0.3
        )

        return response.choices[0].message.content

    except Exception as e:

        st.error(
            f"AI summarization failed: {e}"
        )

        return None


# =========================================================
# FONT LOADING
# =========================================================

def get_font(size, bold=False):

    possible_fonts = []

    if bold:

        possible_fonts = [
            r"C:\Windows\Fonts\arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ]

    else:

        possible_fonts = [
            r"C:\Windows\Fonts\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]

    for path in possible_fonts:

        if os.path.exists(path):

            return ImageFont.truetype(
                path,
                size
            )

    return ImageFont.load_default()


# =========================================================
# CREATE SHORT NOTES IMAGE
# =========================================================

def create_notes_image(summary):

    width = 1400
    height = 1800

    image = Image.new(
        "RGB",
        (width, height),
        "white"
    )

    draw = ImageDraw.Draw(image)

    title_font = get_font(52, True)
    heading_font = get_font(34, True)
    body_font = get_font(27, False)

    x = 80
    y = 70

    # Header
    draw.text(
        (x, y),
        "LECTURELENS",
        font=title_font,
        fill="black"
    )

    y += 90

    draw.line(
        (x, y, width - x, y),
        fill="black",
        width=3
    )

    y += 50

    # Process sections
    sections = summary.split("\n")

    for line in sections:

        line = line.strip()

        if not line:
            y += 15
            continue

        upper = line.upper()

        if (
            upper.startswith("TITLE:")
            or upper.startswith("SUMMARY:")
            or upper.startswith("KEY POINTS:")
            or upper.startswith("KEYWORDS:")
            or upper.startswith("QUICK REVISION:")
        ):

            heading = line.replace(":", "")

            draw.text(
                (x, y),
                heading,
                font=heading_font,
                fill="black"
            )

            y += 55

        else:

            wrapped = textwrap.wrap(
                line,
                width=70
            )

            for part in wrapped:

                draw.text(
                    (x, y),
                    part,
                    font=body_font,
                    fill="black"
                )

                y += 42

        if y > height - 100:
            break

    return image


# =========================================================
# MAIN PROCESSING
# =========================================================

if uploaded_file:

    file_name = uploaded_file.name.lower()

    st.divider()

    # -----------------------------------------------------
    # IMAGE
    # -----------------------------------------------------

    if file_name.endswith(
        (".png", ".jpg", ".jpeg", ".webp")
    ):

        image = Image.open(uploaded_file)

        st.subheader("📷 Uploaded Image")

        st.image(
            image,
            use_container_width=True
        )

        if st.button(
            "🚀 Extract & Summarize",
            type="primary"
        ):

            with st.spinner(
                "Reading image with OCR..."
            ):

                extracted_text = extract_text_from_image(
                    image
                )

            if not extracted_text:

                st.warning(
                    "No readable text was detected."
                )

            else:

                st.subheader("🔎 Extracted Text")

                st.text_area(
                    "OCR Result",
                    extracted_text,
                    height=250
                )

                with st.spinner(
                    "Creating AI short notes..."
                ):

                    summary = generate_summary(
                        extracted_text
                    )

                if summary:

                    st.subheader(
                        "🤖 AI Short Notes"
                    )

                    st.markdown(summary)

                    note_image = create_notes_image(
                        summary
                    )

                    st.subheader(
                        "🖼️ Generated Short Notes"
                    )

                    st.image(
                        note_image,
                        use_container_width=True
                    )

                    image_path = os.path.join(
                        tempfile.gettempdir(),
                        "lecturelens_notes.png"
                    )

                    note_image.save(
                        image_path
                    )

                    with open(
                        image_path,
                        "rb"
                    ) as f:

                        st.download_button(
                            "⬇️ Download Short Notes",
                            f,
                            file_name="LectureLens_Short_Notes.png",
                            mime="image/png"
                        )


    # -----------------------------------------------------
    # VIDEO
    # -----------------------------------------------------

    elif file_name.endswith(
        (".mp4", ".mov", ".avi")
    ):

        st.subheader("🎥 Lecture Video")

        st.video(
            uploaded_file
        )

        if st.button(
            "🚀 Analyze Lecture",
            type="primary"
        ):

            temp_video = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=os.path.splitext(
                    uploaded_file.name
                )[1]
            )

            temp_video.write(
                uploaded_file.getbuffer()
            )

            temp_video.close()

            with st.spinner(
                "Extracting frames and reading text..."
            ):

                results = extract_text_from_video(
                    temp_video.name,
                    frame_interval
                )

            os.unlink(temp_video.name)

            results = remove_duplicates(
                results
            )

            if not results:

                st.warning(
                    "No readable text was detected "
                    "in the video."
                )

            else:

                st.success(
                    f"Detected text from {len(results)} "
                    f"lecture frames."
                )

                st.subheader(
                    "⏱️ Timestamped Lecture Text"
                )

                combined_text = ""

                for item in results:

                    minutes = int(
                        item["time"] // 60
                    )

                    seconds = int(
                        item["time"] % 60
                    )

                    timestamp = (
                        f"{minutes:02d}:{seconds:02d}"
                    )

                    st.markdown(
                        f"**⏱️ {timestamp}**"
                    )

                    st.write(
                        item["text"]
                    )

                    combined_text += (
                        f"[{timestamp}] "
                        f"{item['text']}\n"
                    )

                with st.spinner(
                    "Creating AI lecture notes..."
                ):

                    summary = generate_summary(
                        combined_text
                    )

                if summary:

                    st.subheader(
                        "🤖 AI Short Notes"
                    )

                    st.markdown(summary)

                    note_image = create_notes_image(
                        summary
                    )

                    st.subheader(
                        "🖼️ Generated Revision Note"
                    )

                    st.image(
                        note_image,
                        use_container_width=True
                    )

                    image_path = os.path.join(
                        tempfile.gettempdir(),
                        "lecturelens_video_notes.png"
                    )

                    note_image.save(
                        image_path
                    )

                    with open(
                        image_path,
                        "rb"
                    ) as f:

                        st.download_button(
                            "⬇️ Download Revision Note",
                            f,
                            file_name="LectureLens_Lecture_Notes.png",
                            mime="image/png"
                        )