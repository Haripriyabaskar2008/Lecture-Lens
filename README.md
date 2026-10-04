# Lecture-Lens
 LectureLens

### AI-Powered Lecture-to-Revision Notes Generator

LectureLens is an AI-powered educational application that converts lecture images and videos into concise, easy-to-revise notes using OCR and Large Language Models.

It extracts text from lecture materials, summarizes the content using AI, and automatically generates a colourful infographic-style revision note that students can download and use for quick revision.

---

##  Live Application

 **Try LectureLens:**  
[Open LectureLens](https://lecture-lens-cytycg7kxkt7vcz2swlqp5.streamlit.app/)

---

##  Application Screenshots

### Home Page
<img width="955" height="318" alt="Screenshot 2026-10-04 173315" src="https://github.com/user-attachments/assets/04a5f620-a972-4c03-81d9-0452ccbbdb1d" />



###  Image OCR & AI Summary

<img width="959" height="408" alt="Screenshot 2026-10-04 173350" src="https://github.com/user-attachments/assets/ca5c30ad-fa28-46f4-8a8c-78b490adaf0f" />
<img width="957" height="397" alt="Screenshot 2026-10-04 173408" src="https://github.com/user-attachments/assets/f6f3d4e1-e9ce-4119-a971-cb57d5af6966" />



###  AI-Generated Visual Revision Notes

<img width="959" height="382" alt="Screenshot 2026-10-04 173439" src="https://github.com/user-attachments/assets/41f9951b-15e2-484a-bff5-872a78b3ad67" />
<img width="947" height="292" alt="Screenshot 2026-10-04 173426" src="https://github.com/user-attachments/assets/5cdfbca1-9866-4c62-a35c-cbfc81522be3" />
<img width="1400" height="1900" alt="LectureLens_Lecture_Notes" src="https://github.com/user-attachments/assets/17040aaa-2b5d-4baa-b97b-3e9a703796c6" />





---

## Features

-  Upload lecture images
-  Upload lecture videos
-  Extract text using OCR
-  Generate AI-powered summaries
-  Identify important key concepts
-  Extract important keywords
-  Generate quick revision content
-  Create colourful infographic-style notes
-  Download revision notes as PNG
-  Useful for students, teachers and self-learning
-  Deployed using Streamlit

---

##  How LectureLens Works

```text
Lecture Image / Video
          ↓
       OCR Engine
          ↓
    Extracted Text
          ↓
    AI Summarization
          ↓
   Structured Notes
          ↓
 Colourful Infographic
          ↓
 Downloadable Revision Image
🔧 Technologies Used
Technology	Purpose
Python	Application development
Streamlit	Web application and deployment
Tesseract OCR	Text extraction from images
OpenCV	Image processing and video frame extraction
Pillow	Infographic generation
Hugging Face	AI-powered summarization
Qwen LLM	Lecture content summarization
AI Capabilities:

LectureLens uses an AI language model to transform raw OCR text into structured educational content.

The generated output includes:

Title
Summary
Key Concepts
Keywords
Quick Revision

The structured information is then converted into a visually appealing revision infographic.

 Visual Revision Notes

Instead of displaying only plain AI-generated text, LectureLens automatically creates a colourful revision card containing:

Topic title
Short summary
Numbered key concepts
Important keywords
Quick revision section

This makes the generated content easier to read, remember and revise.

 Video Processing

LectureLens can also process lecture videos.

The application:

Uploads the lecture video.
Extracts frames at selected intervals.
Applies OCR to the frames.
Removes repeated content.
Combines the extracted lecture text.
Sends the content to the AI model.
Generates concise revision notes.
Creates a visual revision infographic.

This is especially useful for lectures where important information is displayed on slides or boards.

Use Cases:
Students

Convert classroom slides, handwritten notes and lecture recordings into quick revision material.

Teachers

Create concise revision material from lecture slides.

Self-Learners

Convert educational content into structured notes for faster revision.

Exam Preparation

Generate quick revision sheets from large amounts of lecture content.

 Problem Statement

Students often spend significant time converting lengthy lecture materials into short revision notes.

LectureLens reduces this effort by automatically:

Extracting → Understanding → Summarizing → Visualizing

lecture content in a single workflow.

 What Makes LectureLens Different?

Traditional OCR applications mainly extract text.

LectureLens goes beyond simple text extraction by combining:

OCR + AI Summarization + Visual Note Generation

This transforms unstructured lecture content into a structured and visually engaging revision resource.

Security

The Hugging Face API token is stored using Streamlit Secrets and is not included in the source code.

Sensitive credentials are excluded from the GitHub repository.

 Installation

Clone the repository:

git clone YOUR_GITHUB_REPOSITORY_URL

Navigate to the project:

cd LectureLens

Install the required packages:

pip install -r requirements.txt

Run the application:
https://lecture-lens-cytycg7kxkt7vcz2swlqp5.streamlit.app/

 Project Structure
LectureLens/
│
├── app.py
├── requirements.txt
├── .gitignore
├── README.md
└── screenshots/
    ├── home.png
    ├── image-ocr.png
    ├── revision-notes.png
    └── video-processing.png
 Future Enhancements
 Multi-language OCR
 Audio-to-text lecture transcription
 Automatic quiz generation
 AI-generated exam questions
 PDF lecture support
 Subject-wise note organization
 Mobile-friendly interface
 Personalized revision recommendations
Developer:

HARI PRIYA.B

B.Sc. Computer Science with Artificial Intelligence

⭐ Project

If you find LectureLens useful, consider giving the repository a ⭐ on GitHub.
