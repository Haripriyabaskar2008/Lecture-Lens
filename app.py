
import streamlit as st
import cv2
import pytesseract
import numpy as np
import os
import re
import textwrap
from PIL import Image, ImageDraw, ImageFont
from google import genai


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="LectureLens - AI Revision Notes",
    page_icon="📚",
    layout="wide"
)


# ============================================================
# TESSERACT CONFIGURATION
# ============================================================

windows_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if os.path.exists(windows_tesseract):
    pytesseract.pytesseract.tesseract_cmd = windows_tesseract


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None


# ============================================================
# CUSTOM STYLING
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 42px;
        font-weight: 800;
        text-align: center;
        margin-bottom: 5px;
    }

    .subtitle {
        text-align: center;
        font-size: 18px;
        margin-bottom: 25px;
    }

    .info-box {
        padding: 15px;
        border-radius: 15px;
        background-color: #f0f4ff;
        margin-bottom: 15px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# TITLE
# ============================================================

st.markdown(
    '<div class="main-title">📚 LectureLens</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">AI-Powered Lecture-to-Revision Notes Generator</div>',
    unsafe_allow_html=True
)

st.write(
    "Upload a lecture image or video. LectureLens extracts visible text, "
    "summarizes it using AI, and creates colourful revision notes."
)


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def preprocess_image(image):
    """
    Preprocess image to improve OCR accuracy.
    """

    image_array = np.array(image)

    # Convert RGB to BGR
    image_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)

    # Convert to grayscale
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    # Resize image
    height, width = gray.shape

    if width < 1500:
        scale = 1500 / width
        gray = cv2.resize(
            gray,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC
        )

    # Remove small noise
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # Threshold
    _, threshold = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return threshold


# ============================================================
# IMAGE OCR
# ============================================================

def extract_text_from_image(image):
    """
    Extract text from an image using Tesseract OCR.
    """

    processed = preprocess_image(image)

    text = pytesseract.image_to_string(
        processed,
        config="--psm 6"
    )

    return text.strip()


# ============================================================
# VIDEO OCR
# ============================================================

def extract_text_from_video(video_path, interval_seconds=4):
    """
    Extract text from video frames.

    The video itself is not directly read by OCR.
    Frames are extracted at regular intervals and OCR
    is applied to each frame.
    """

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        return ""

    fps = cap.get(cv2.CAP_PROP_FPS)

    if fps <= 0:
        fps = 30

    frame_interval = int(fps * interval_seconds)

    texts = []

    frame_number = 0
    last_text = ""

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        if frame_number % frame_interval == 0:

            rgb_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            pil_image = Image.fromarray(rgb_frame)

            text = extract_text_from_image(pil_image)

            if text:

                # Normalize for duplicate comparison
                normalized_current = re.sub(
                    r"\s+",
                    " ",
                    text.lower()
                ).strip()

                normalized_previous = re.sub(
                    r"\s+",
                    " ",
                    last_text.lower()
                ).strip()

                # Avoid duplicate slide text
                if normalized_current != normalized_previous:

                    texts.append(text)
                    last_text = text

        frame_number += 1

    cap.release()

    return "\n\n".join(texts)


# ============================================================
# GEMINI AI SUMMARIZATION
# ============================================================

def generate_ai_summary(extracted_text):
    """
    Send OCR text to Gemini and generate structured
    educational revision content.
    """

    if not client:
        raise Exception(
            "GEMINI_API_KEY is missing. "
            "Add GEMINI_API_KEY to Streamlit Secrets."
        )

    prompt = f"""
You are an educational AI assistant.

Convert the following lecture text into concise,
accurate revision notes for a college student.

IMPORTANT:
- Use ONLY information present in the provided text.
- Do not invent facts.
- Keep the language simple and clear.
- Do not use Markdown symbols such as #, *, or **.
- Keep the answer structured exactly using the labels below.

Return exactly:

TITLE:
A short suitable title.

SUMMARY:
A concise paragraph explaining the main concept.

KEY POINTS:
1. First important point
2. Second important point
3. Third important point
4. Fourth important point
5. Fifth important point

KEYWORDS:
keyword1, keyword2, keyword3, keyword4, keyword5

QUICK REVISION:
A very short revision paragraph containing the most important things to remember.

LECTURE TEXT:
{extracted_text}
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    if not response.text:
        raise Exception("Gemini returned an empty response.")

    return response.text.strip()


# ============================================================
# PARSE AI RESPONSE
# ============================================================

def parse_summary(response):

    result = {
        "title": "Lecture Revision Notes",
        "summary": "",
        "key_points": [],
        "keywords": [],
        "quick_revision": ""
    }

    title_match = re.search(
        r"TITLE:\s*(.*?)(?=\nSUMMARY:|\Z)",
        response,
        re.S | re.I
    )

    summary_match = re.search(
        r"SUMMARY:\s*(.*?)(?=\nKEY POINTS:|\Z)",
        response,
        re.S | re.I
    )

    points_match = re.search(
        r"KEY POINTS:\s*(.*?)(?=\nKEYWORDS:|\Z)",
        response,
        re.S | re.I
    )

    keywords_match = re.search(
        r"KEYWORDS:\s*(.*?)(?=\nQUICK REVISION:|\Z)",
        response,
        re.S | re.I
    )

    revision_match = re.search(
        r"QUICK REVISION:\s*(.*)",
        response,
        re.S | re.I
    )

    if title_match:
        result["title"] = title_match.group(1).strip()

    if summary_match:
        result["summary"] = summary_match.group(1).strip()

    if points_match:

        points_text = points_match.group(1).strip()

        points = re.findall(
            r"(?:^|\n)\s*(?:\d+[\.\)]|-)\s*(.*)",
            points_text
        )

        result["key_points"] = [
            p.strip()
            for p in points
            if p.strip()
        ]

    if keywords_match:

        keyword_text = keywords_match.group(1).strip()

        result["keywords"] = [
            k.strip()
            for k in keyword_text.split(",")
            if k.strip()
        ]

    if revision_match:
        result["quick_revision"] = revision_match.group(1).strip()

    return result


# ============================================================
# FONT FUNCTION
# ============================================================

def get_font(size, bold=False):

    font_paths = []

    if bold:
        font_paths = [
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\calibrib.ttf"
        ]
    else:
        font_paths = [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\calibri.ttf"
        ]

    for path in font_paths:

        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


# ============================================================
# TEXT WRAPPING
# ============================================================

def draw_wrapped_text(
    draw,
    text,
    position,
    font,
    max_width,
    line_spacing=8
):

    x, y = position

    words = text.split()
    current_line = ""

    for word in words:

        test_line = (
            current_line + " " + word
        ).strip()

        bbox = draw.textbbox(
            (0, 0),
            test_line,
            font=font
        )

        width = bbox[2] - bbox[0]

        if width <= max_width:
            current_line = test_line

        else:

            draw.text(
                (x, y),
                current_line,
                font=font,
                fill=(35, 35, 55)
            )

            y += (
                bbox[3] - bbox[1]
            ) + line_spacing

            current_line = word

    if current_line:

        draw.text(
            (x, y),
            current_line,
            font=font,
            fill=(35, 35, 55)
        )

        bbox = draw.textbbox(
            (0, 0),
            current_line,
            font=font
        )

        y += (
            bbox[3] - bbox[1]
        ) + line_spacing

    return y


# ============================================================
# INFOGRAPHIC GENERATOR
# ============================================================

def create_revision_image(data):

    width = 1400
    height = 1800

    image = Image.new(
        "RGB",
        (width, height),
        (248, 249, 255)
    )

    draw = ImageDraw.Draw(image)

    # Fonts
    title_font = get_font(48, bold=True)
    section_font = get_font(30, bold=True)
    body_font = get_font(24)
    small_font = get_font(21)

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    draw.rounded_rectangle(
        (40, 35, width - 40, 190),
        radius=30,
        fill=(92, 75, 170)
    )

    title = data["title"]

    draw.text(
        (80, 65),
        title,
        font=title_font,
        fill="white"
    )

    draw.text(
        (82, 125),
        "LECTURELENS • AI REVISION NOTES",
        font=small_font,
        fill="white"
    )

    # --------------------------------------------------------
    # SUMMARY CARD
    # --------------------------------------------------------

    y = 230

    draw.rounded_rectangle(
        (40, y, width - 40, y + 280),
        radius=25,
        fill=(225, 239, 255)
    )

    draw.text(
        (75, y + 25),
        "SUMMARY",
        font=section_font,
        fill=(45, 70, 130)
    )

    draw_wrapped_text(
        draw,
        data["summary"],
        (75, y + 80),
        body_font,
        width - 170
    )

    y += 315

    # --------------------------------------------------------
    # KEY POINTS
    # --------------------------------------------------------

    points = data["key_points"]

    card_height = max(
        100,
        90 + len(points) * 75
    )

    draw.rounded_rectangle(
        (40, y, width - 40, y + card_height),
        radius=25,
        fill=(255, 241, 220)
    )

    draw.text(
        (75, y + 25),
        "KEY POINTS",
        font=section_font,
        fill=(150, 90, 25)
    )

    point_y = y + 80

    for index, point in enumerate(points, 1):

        draw.ellipse(
            (75, point_y, 115, point_y + 40),
            fill=(245, 166, 35)
        )

        draw.text(
            (89, point_y + 5),
            str(index),
            font=get_font(20, bold=True),
            fill="white"
        )

        draw_wrapped_text(
            draw,
            point,
            (135, point_y),
            body_font,
            width - 220,
            line_spacing=5
        )

        point_y += 70

    y += card_height + 35

    # --------------------------------------------------------
    # KEYWORDS
    # --------------------------------------------------------

    keyword_card_height = 180

    draw.rounded_rectangle(
        (40, y, width - 40, y + keyword_card_height),
        radius=25,
        fill=(232, 248, 235)
    )

    draw.text(
        (75, y + 25),
        "KEYWORDS",
        font=section_font,
        fill=(45, 120, 70)
    )

    keyword_y = y + 85
    keyword_x = 75

    for keyword in data["keywords"]:

        keyword = keyword.strip()

        bbox = draw.textbbox(
            (0, 0),
            keyword,
            font=small_font
        )

        keyword_width = (
            bbox[2] - bbox[0]
        ) + 40

        if keyword_x + keyword_width > width - 75:

            keyword_x = 75
            keyword_y += 55

        draw.rounded_rectangle(
            (
                keyword_x,
                keyword_y,
                keyword_x + keyword_width,
                keyword_y + 42
            ),
            radius=20,
            fill=(120, 190, 140)
        )

        draw.text(
            (keyword_x + 20, keyword_y + 8),
            keyword,
            font=small_font,
            fill="white"
        )

        keyword_x += keyword_width + 12

    y += keyword_card_height + 35

    # --------------------------------------------------------
    # QUICK REVISION
    # --------------------------------------------------------

    revision_height = 300

    draw.rounded_rectangle(
        (40, y, width - 40, y + revision_height),
        radius=25,
        fill=(248, 229, 250)
    )

    draw.text(
        (75, y + 25),
        "QUICK REVISION",
        font=section_font,
        fill=(135, 65, 145)
    )

    draw_wrapped_text(
        draw,
        data["quick_revision"],
        (75, y + 85),
        body_font,
        width - 170
    )

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    draw.text(
        (75, height - 70),
        "Generated by LectureLens • OCR + Gemini AI + Pillow",
        font=small_font,
        fill=(100, 100, 120)
    )

    return image


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ LectureLens")

    input_type = st.radio(
        "Choose input type",
        ["Lecture Image", "Lecture Video"]
    )

    if input_type == "Lecture Video":

        interval = st.slider(
            "Frame interval (seconds)",
            min_value=2,
            max_value=10,
            value=4
        )

    st.markdown("---")

    st.info(
        "LectureLens uses Tesseract OCR for text extraction, "
        "Gemini for AI summarization and Pillow for visual "
        "revision-note generation."
    )


# ============================================================
# IMAGE INPUT
# ============================================================

if input_type == "Lecture Image":

    uploaded_file = st.file_uploader(
        "Upload Lecture Image",
        type=["png", "jpg", "jpeg"]
    )

    if uploaded_file:

        image = Image.open(uploaded_file).convert("RGB")

        st.image(
            image,
            caption="Uploaded Lecture Image",
            use_container_width=True
        )

        if st.button(
            "✨ Generate Revision Notes",
            use_container_width=True
        ):

            with st.spinner(
                "🔍 Extracting text using OCR..."
            ):

                extracted_text = extract_text_from_image(
                    image
                )

            if not extracted_text:

                st.error(
                    "No readable text was detected in the image."
                )

            else:

                with st.expander("🔎 Extracted OCR Text"):

                    st.write(extracted_text)

                try:

                    with st.spinner(
                        "🧠 Gemini is creating your revision notes..."
                    ):

                        ai_response = generate_ai_summary(
                            extracted_text
                        )

                    summary_data = parse_summary(
                        ai_response
                    )

                    with st.spinner(
                        "🎨 Creating colourful revision notes..."
                    ):

                        revision_image = create_revision_image(
                            summary_data
                        )

                    st.success(
                        "🎉 Revision notes generated successfully!"
                    )

                    st.image(
                        revision_image,
                        caption="AI Revision Notes",
                        use_container_width=True
                    )

                    # Convert image to bytes
                    from io import BytesIO

                    image_bytes = BytesIO()

                    revision_image.save(
                        image_bytes,
                        format="PNG"
                    )

                    st.download_button(
                        label="⬇️ Download Revision Notes",
                        data=image_bytes.getvalue(),
                        file_name="LectureLens_Revision_Notes.png",
                        mime="image/png",
                        use_container_width=True
                    )

                except Exception as e:

                    st.error(
                        f"AI summarization failed: {e}"
                    )


# ============================================================
# VIDEO INPUT
# ============================================================

else:

    uploaded_video = st.file_uploader(
        "Upload Lecture Video",
        type=["mp4", "mov", "avi", "mkv"]
    )

    if uploaded_video:

        st.video(uploaded_video)

        if st.button(
            "🎬 Process Lecture Video",
            use_container_width=True
        ):

            temp_video_path = None

            try:

                import tempfile

                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=".mp4"
                ) as temp_video:

                    temp_video.write(
                        uploaded_video.read()
                    )

                    temp_video_path = temp_video.name

                with st.spinner(
                    "🎞️ Extracting lecture frames and reading text..."
                ):

                    extracted_text = extract_text_from_video(
                        temp_video_path,
                        interval_seconds=interval
                    )

                if not extracted_text:

                    st.error(
                        "No readable text was detected in the video."
                    )

                else:

                    with st.expander(
                        "🔎 Extracted Video OCR Text"
                    ):

                        st.write(extracted_text)

                    with st.spinner(
                        "🧠 Gemini is creating revision notes..."
                    ):

                        ai_response = generate_ai_summary(
                            extracted_text
                        )

                    summary_data = parse_summary(
                        ai_response
                    )

                    with st.spinner(
                        "🎨 Creating colourful revision notes..."
                    ):

                        revision_image = create_revision_image(
                            summary_data
                        )

                    st.success(
                        "🎉 Video revision notes generated successfully!"
                    )

                    st.image(
                        revision_image,
                        caption="AI Revision Notes",
                        use_container_width=True
                    )

                    from io import BytesIO

                    image_bytes = BytesIO()

                    revision_image.save(
                        image_bytes,
                        format="PNG"
                    )

                    st.download_button(
                        label="⬇️ Download Revision Notes",
                        data=image_bytes.getvalue(),
                        file_name="LectureLens_Video_Revision_Notes.png",
                        mime="image/png",
                        use_container_width=True
                    )

            except Exception as e:

                st.error(
                    f"Video processing failed: {e}"
                )

            finally:

                if temp_video_path and os.path.exists(
                    temp_video_path
                ):

                    try:
                        os.remove(temp_video_path)
                    except:
                        pass


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "LectureLens | OCR + OpenCV + Gemini AI + Pillow + Streamlit"
)
