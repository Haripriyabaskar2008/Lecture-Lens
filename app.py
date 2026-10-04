import streamlit as st
import pytesseract
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
import tempfile
import os
import shutil
import re
import textwrap
from huggingface_hub import InferenceClient


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="LectureLens",
    page_icon="🎓",
    layout="wide"
)


# ============================================================
# TESSERACT CONFIGURATION
# ============================================================

windows_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if os.path.exists(windows_tesseract):
    pytesseract.pytesseract.tesseract_cmd = windows_tesseract

elif shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")


# ============================================================
# CUSTOM UI
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        text-align: center;
        font-size: 44px;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .subtitle {
        text-align: center;
        font-size: 18px;
        color: #64748B;
        margin-bottom: 30px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🎓 LectureLens</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Transform lectures and documents into smart visual revision notes'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Settings")

    frame_interval = st.slider(
        "Video frame interval (seconds)",
        min_value=2,
        max_value=10,
        value=4
    )

    st.info(
        "For faster processing, use a short lecture video "
        "during the demonstration."
    )


# ============================================================
# FILE UPLOAD
# ============================================================

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


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def preprocess_image(image):

    image = image.convert("RGB")

    img = np.array(image)

    img = cv2.cvtColor(
        img,
        cv2.COLOR_RGB2BGR
    )

    gray = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2GRAY
    )

    # Increase size for better OCR
    gray = cv2.resize(
        gray,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC
    )

    # Remove small noise
    gray = cv2.GaussianBlur(
        gray,
        (3, 3),
        0
    )

    # Convert to black and white
    _, threshold = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return Image.fromarray(threshold)


# ============================================================
# OCR IMAGE
# ============================================================

def extract_text_from_image(image):

    processed = preprocess_image(image)

    text = pytesseract.image_to_string(
        processed,
        config="--psm 6"
    )

    return text.strip()


# ============================================================
# OCR VIDEO
# ============================================================

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

            text = extract_text_from_image(
                image
            )

            if text:

                results.append(
                    {
                        "time": current_time,
                        "text": text
                    }
                )

            next_capture += interval

        frame_count += 1

    cap.release()

    return results


# ============================================================
# REMOVE DUPLICATE VIDEO TEXT
# ============================================================

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

        if current.lower() == previous.lower():
            continue

        cleaned.append(
            {
                "time": item["time"],
                "text": current
            }
        )

        previous_text = current

    return cleaned


# ============================================================
# AI SUMMARY
# ============================================================

def generate_summary(text):

    try:

        token = st.secrets["HF_TOKEN"]

    except Exception:

        token = os.getenv(
            "HF_TOKEN",
            ""
        )

    if not token:

        st.error(
            "HF_TOKEN is missing. "
            "Add it in Streamlit Secrets."
        )

        return None

    client = InferenceClient(
        api_key=token
    )

    prompt = f"""
You are LectureLens, an educational AI note-making assistant.

Analyze the following OCR-extracted lecture content.

Create concise and accurate revision notes.

Return ONLY these sections:

TITLE:
Give a short topic title.

SUMMARY:
Write a simple 3 to 5 sentence explanation.

KEY POINTS:
Give 4 to 6 important points.
Each point should be a complete sentence.
Do not use markdown headings.

KEYWORDS:
Give 5 to 8 important keywords separated by commas.

QUICK REVISION:
Write a short exam-oriented revision paragraph.

IMPORTANT:
- Do not use # symbols.
- Do not use markdown headings.
- Do not use ** bold formatting.
- Do not invent information.
- Keep the language simple and student-friendly.

SOURCE CONTENT:

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


# ============================================================
# FONT LOADER
# ============================================================

def get_font(size, bold=False):

    if bold:

        font_paths = [
            r"C:\Windows\Fonts\arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ]

    else:

        font_paths = [
            r"C:\Windows\Fonts\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]

    for path in font_paths:

        if os.path.exists(path):

            return ImageFont.truetype(
                path,
                size
            )

    return ImageFont.load_default()


# ============================================================
# CLEAN AI TEXT
# ============================================================

def clean_ai_text(text):

    text = re.sub(
        r"#{1,6}\s*",
        "",
        text
    )

    text = text.replace(
        "**",
        ""
    )

    text = text.replace(
        "__",
        ""
    )

    text = text.replace(
        "`",
        ""
    )

    return text.strip()


# ============================================================
# PARSE AI SUMMARY
# ============================================================

def parse_summary(summary):

    title = "Lecture Revision Notes"

    summary_text = ""

    key_points = []

    keywords = []

    quick_revision = ""

    current_section = ""

    lines = summary.splitlines()

    for line in lines:

        line = line.strip()

        if not line:
            continue

        line = clean_ai_text(line)

        upper = line.upper()

        if upper.startswith("TITLE:"):

            title = line.split(
                ":",
                1
            )[1].strip()

            current_section = "title"

        elif upper.startswith("SUMMARY:"):

            current_section = "summary"

            remaining = line.split(
                ":",
                1
            )[1].strip()

            if remaining:
                summary_text += remaining + " "

        elif upper.startswith("KEY POINTS:"):

            current_section = "points"

        elif upper.startswith("KEYWORDS:"):

            current_section = "keywords"

            remaining = line.split(
                ":",
                1
            )[1].strip()

            if remaining:

                keywords.extend(
                    [
                        x.strip()
                        for x in remaining.split(",")
                        if x.strip()
                    ]
                )

        elif upper.startswith("QUICK REVISION:"):

            current_section = "revision"

            remaining = line.split(
                ":",
                1
            )[1].strip()

            if remaining:
                quick_revision += remaining + " "

        else:

            if current_section == "summary":

                summary_text += line + " "

            elif current_section == "points":

                line = re.sub(
                    r"^[-•*]\s*",
                    "",
                    line
                )

                if line:
                    key_points.append(line)

            elif current_section == "keywords":

                parts = line.split(",")

                for part in parts:

                    part = part.strip()

                    if part:
                        keywords.append(part)

            elif current_section == "revision":

                quick_revision += line + " "

    return (
        title.strip(),
        summary_text.strip(),
        key_points[:6],
        keywords[:8],
        quick_revision.strip()
    )


# ============================================================
# CREATE COLOURFUL INFOGRAPHIC
# ============================================================

def create_notes_image(summary):

    # --------------------------------------------------------
    # Parse content
    # --------------------------------------------------------

    (
        title,
        summary_text,
        key_points,
        keywords,
        quick_revision
    ) = parse_summary(summary)

    # --------------------------------------------------------
    # Canvas
    # --------------------------------------------------------

    width = 1400
    height = 1900

    image = Image.new(
        "RGB",
        (width, height),
        "#F6F8FC"
    )

    draw = ImageDraw.Draw(image)

    # --------------------------------------------------------
    # Colours
    # --------------------------------------------------------

    NAVY = "#172554"
    BLUE = "#2563EB"
    PURPLE = "#7C3AED"
    CYAN = "#0891B2"
    GREEN = "#059669"
    ORANGE = "#EA580C"
    RED = "#DC2626"

    DARK = "#1E293B"
    GREY = "#64748B"
    WHITE = "#FFFFFF"

    LIGHT_BLUE = "#EFF6FF"
    LIGHT_PURPLE = "#F5F3FF"
    LIGHT_GREEN = "#ECFDF5"
    LIGHT_ORANGE = "#FFF7ED"
    LIGHT_CYAN = "#ECFEFF"

    # --------------------------------------------------------
    # Fonts
    # --------------------------------------------------------

    title_font = get_font(
        52,
        True
    )

    subtitle_font = get_font(
        24,
        True
    )

    section_font = get_font(
        30,
        True
    )

    body_font = get_font(
        23,
        False
    )

    small_font = get_font(
        18,
        False
    )

    number_font = get_font(
        21,
        True
    )

    keyword_font = get_font(
        19,
        True
    )

    # --------------------------------------------------------
    # Helper
    # --------------------------------------------------------

    def rounded_box(
        x1,
        y1,
        x2,
        y2,
        fill,
        radius=28
    ):

        draw.rounded_rectangle(
            (
                x1,
                y1,
                x2,
                y2
            ),
            radius=radius,
            fill=fill
        )

    # ========================================================
    # HEADER
    # ========================================================

    rounded_box(
        45,
        40,
        width - 45,
        275,
        NAVY,
        35
    )

    # Decorative circles

    draw.ellipse(
        (
            width - 245,
            60,
            width - 105,
            200
        ),
        fill=PURPLE
    )

    draw.ellipse(
        (
            width - 175,
            135,
            width - 75,
            235
        ),
        fill=CYAN
    )

    draw.text(
        (90, 72),
        "LECTURELENS",
        font=subtitle_font,
        fill="#BFDBFE"
    )

    # Title

    title = title[:70]

    title_lines = textwrap.wrap(
        title,
        width=31
    )

    title_y = 115

    for line in title_lines[:2]:

        draw.text(
            (90, title_y),
            line,
            font=title_font,
            fill=WHITE
        )

        title_y += 58

    draw.text(
        (90, 225),
        "AI-GENERATED REVISION NOTES",
        font=small_font,
        fill="#CBD5E1"
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    y = 315

    rounded_box(
        55,
        y,
        width - 55,
        y + 285,
        LIGHT_BLUE
    )

    draw.rectangle(
        (
            55,
            y,
            70,
            y + 285
        ),
        fill=BLUE
    )

    draw.text(
        (100, y + 30),
        "SUMMARY",
        font=section_font,
        fill=BLUE
    )

    summary_lines = textwrap.wrap(
        summary_text,
        width=82
    )

    text_y = y + 85

    for line in summary_lines[:7]:

        draw.text(
            (100, text_y),
            line,
            font=body_font,
            fill=DARK
        )

        text_y += 34

    # ========================================================
    # KEY POINTS
    # ========================================================

    y = y + 320

    draw.text(
        (60, y),
        "KEY CONCEPTS",
        font=section_font,
        fill=PURPLE
    )

    y += 62

    card_backgrounds = [
        LIGHT_PURPLE,
        LIGHT_BLUE,
        LIGHT_GREEN,
        LIGHT_ORANGE,
        "#FEF2F2",
        LIGHT_CYAN
    ]

    accents = [
        PURPLE,
        BLUE,
        GREEN,
        ORANGE,
        RED,
        CYAN
    ]

    for index, point in enumerate(key_points):

        card_height = 112

        rounded_box(
            55,
            y,
            width - 55,
            y + card_height,
            card_backgrounds[
                index % len(card_backgrounds)
            ],
            24
        )

        accent = accents[
            index % len(accents)
        ]

        # Number circle

        draw.ellipse(
            (
                82,
                y + 30,
                128,
                y + 76
            ),
            fill=accent
        )

        number_text = str(
            index + 1
        )

        draw.text(
            (97, y + 35),
            number_text,
            font=number_font,
            fill=WHITE
        )

        # Point text

        point_lines = textwrap.wrap(
            point,
            width=76
        )

        point_y = y + 22

        for line in point_lines[:2]:

            draw.text(
                (155, point_y),
                line,
                font=body_font,
                fill=DARK
            )

            point_y += 32

        y += card_height + 15

    # ========================================================
    # KEYWORDS
    # ========================================================

    y += 15

    draw.text(
        (60, y),
        "KEYWORDS",
        font=section_font,
        fill=CYAN
    )

    y += 55

    keyword_x = 60

    keyword_y = y

    for keyword in keywords:

        keyword = keyword[:22]

        bbox = draw.textbbox(
            (0, 0),
            keyword,
            font=keyword_font
        )

        keyword_width = (
            bbox[2] - bbox[0]
        ) + 34

        # Move to next line

        if keyword_x + keyword_width > width - 60:

            keyword_x = 60
            keyword_y += 55

        draw.rounded_rectangle(
            (
                keyword_x,
                keyword_y,
                keyword_x + keyword_width,
                keyword_y + 40
            ),
            radius=18,
            fill="#DFF7FA"
        )

        draw.text(
            (
                keyword_x + 17,
                keyword_y + 8
            ),
            keyword,
            font=keyword_font,
            fill=CYAN
        )

        keyword_x += keyword_width + 10

    # ========================================================
    # QUICK REVISION
    # ========================================================

    keyword_bottom = keyword_y + 50

    y = keyword_bottom + 25

    rounded_box(
        55,
        y,
        width - 55,
        y + 240,
        LIGHT_GREEN,
        28
    )

    draw.rectangle(
        (
            55,
            y,
            70,
            y + 240
        ),
        fill=GREEN
    )

    draw.text(
        (100, y + 30),
        "QUICK REVISION",
        font=section_font,
        fill=GREEN
    )

    revision_lines = textwrap.wrap(
        quick_revision,
        width=82
    )

    revision_y = y + 85

    for line in revision_lines[:5]:

        draw.text(
            (100, revision_y),
            line,
            font=body_font,
            fill=DARK
        )

        revision_y += 34

    # ========================================================
    # FOOTER
    # ========================================================

    draw.text(
        (60, height - 48),
        "LectureLens  •  Learn smarter  •  Revise faster",
        font=small_font,
        fill=GREY
    )

    return image


# ============================================================
# MAIN APPLICATION
# ============================================================

if uploaded_file:

    file_name = uploaded_file.name.lower()

    st.divider()

    # ========================================================
    # IMAGE INPUT
    # ========================================================

    if file_name.endswith(
        (
            ".png",
            ".jpg",
            ".jpeg",
            ".webp"
        )
    ):

        image = Image.open(
            uploaded_file
        )

        st.subheader(
            "📷 Uploaded Image"
        )

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

                extracted_text = (
                    extract_text_from_image(
                        image
                    )
                )

            if not extracted_text:

                st.warning(
                    "No readable text was detected."
                )

            else:

                st.subheader(
                    "🔎 Extracted Text"
                )

                st.text_area(
                    "OCR Result",
                    extracted_text,
                    height=250
                )

                with st.spinner(
                    "Creating AI revision notes..."
                ):

                    summary = generate_summary(
                        extracted_text
                    )

                if summary:

                    st.subheader(
                        "🤖 AI Summary"
                    )

                    st.markdown(
                        summary
                    )

                    # Create colourful infographic

                    notes_image = (
                        create_notes_image(
                            summary
                        )
                    )

                    st.subheader(
                        "🎨 AI-Generated Visual Revision Notes"
                    )

                    st.image(
                        notes_image,
                        use_container_width=True
                    )

                    # Save image

                    image_path = os.path.join(
                        tempfile.gettempdir(),
                        "LectureLens_Notes.png"
                    )

                    notes_image.save(
                        image_path
                    )

                    with open(
                        image_path,
                        "rb"
                    ) as file:

                        st.download_button(
                            label="⬇️ Download Revision Notes",
                            data=file,
                            file_name="LectureLens_Revision_Notes.png",
                            mime="image/png"
                        )


    # ========================================================
    # VIDEO INPUT
    # ========================================================

    elif file_name.endswith(
        (
            ".mp4",
            ".mov",
            ".avi"
        )
    ):

        st.subheader(
            "🎥 Uploaded Lecture"
        )

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
                "Extracting lecture frames and reading text..."
            ):

                results = extract_text_from_video(
                    temp_video.name,
                    frame_interval
                )

            os.unlink(
                temp_video.name
            )

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
                    f"Detected readable content "
                    f"from {len(results)} lecture frames."
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
                    "Creating AI lecture summary..."
                ):

                    summary = generate_summary(
                        combined_text
                    )

                if summary:

                    st.subheader(
                        "🤖 AI Lecture Summary"
                    )

                    st.markdown(
                        summary
                    )

                    # Create colourful infographic

                    notes_image = (
                        create_notes_image(
                            summary
                        )
                    )

                    st.subheader(
                        "🎨 AI-Generated Visual Revision Notes"
                    )

                    st.image(
                        notes_image,
                        use_container_width=True
                    )

                    image_path = os.path.join(
                        tempfile.gettempdir(),
                        "LectureLens_Lecture_Notes.png"
                    )

                    notes_image.save(
                        image_path
                    )

                    with open(
                        image_path,
                        "rb"
                    ) as file:

                        st.download_button(
                            label="⬇️ Download Lecture Notes",
                            data=file,
                            file_name="LectureLens_Lecture_Notes.png",
                            mime="image/png"
                        )