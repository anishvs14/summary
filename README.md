# 📺📝 YouTube & File Summarizer Web App

An AI-powered Flask web app that summarizes both YouTube videos and uploaded content like lecture recordings and study documents. It helps students quickly generate **clean summaries** and **study notes** using advanced AI models.

🚀 [Live Demo on Render](https://summary-app-at70.onrender.com)

---

## 🚀 Features

- 🎥 Summarize **YouTube videos** via URL input
- 📁 Upload **lecture recordings** & **documents** to get summaries, notes, flowchart
  - **Supported formats**: MP3, WAV, MP4, PDF, TXT
- 🧠 Uses **Google Gemini (Generative AI)** for high-quality summarization
- 🧾 Study-friendly output format
- 🌐 Clean, minimal Flask-based web interface
- ☁️ Easily deployable on **Render**

---

## 🛠️ Tech Stack

| Layer        | Tools & Libraries                                                                 |
|--------------|------------------------------------------------------------------------------------|
| **Backend**  | Flask (Python)                                                                    |
| **AI Models**| - Google Generative AI (Gemini) <br> - AssemblyAI (for audio/video transcription) |
| **Utilities**| - `pytube`, `youtube_transcript_api` (YouTube support) <br> - `PyPDF2`, `requests`, `pathlib`, `os`, `python-dotenv` (file handling and config) |
| **Deployment**| Gunicorn + Render                                                               |


---

## 🔑 Environment Setup

### 1. Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY=your_google_gemini_api_key
ASSEMBLYAI_API_KEY=your_assemblyai_api_key (optional for audio/video)
```

### 📦 Installation

### 2. Clone the repo
```
git clone https://github.com/anishvs14/summary.git
cd summary
```

### 3. Create & activate virtual environment
```
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
```

### 4. Install dependencies
```
pip install -r requirements.txt
```

### 5. Run the app
```
python app.py
```
Go to: http://localhost:5000
<br>
<br>
## 🧪 Sample Usage
### 🎥 YouTube Summarizer
Paste YouTube URL like:
https://www.youtube.com/watch?v=dQw4w9WgXcQ

Get transcript → Gemini generates summary

### 📁 File Upload
Upload .mp3, .wav, .mp4, .pdf, .txt

Extracts content or transcribes if needed

Gemini generates a clean summary and notes

---

## 📁 Folder Structure
summary/<br>
├── templates/<br>
│   ├── index.html<br>
│   ├── youtube.html<br>
│   └── results.html<br>
├── static/<br>
│   └── style.css<br>
├── app.py<br>
├── requirements.txt<br>
├── .env (not committed)<br>
└── README.md<br>

---

## 📷 Screenshots
