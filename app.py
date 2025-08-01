import os
import tempfile
from flask import Flask, render_template, request, redirect, url_for, flash
import google.generativeai as genai
import assemblyai as aai
import re 
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from settings import GEMINI_API_KEY, ASSEMBLYAI_API_KEY, YOUTUBE_API_KEY
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)
app.secret_key = os.urandom(24)  # More secure random key
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB upload limit

# Load environment variables (e.g. GOOGLE_API_KEY)
load_dotenv()


# Configure the APIs with those keys
genai.configure(api_key=GEMINI_API_KEY)
aai.settings.api_key = ASSEMBLYAI_API_KEY

# Supported file formats
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'mp4', 'pdf', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def transcribe_audio(file_path):
    try:
        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(speaker_labels=True)
        transcript = transcriber.transcribe(file_path, config=config)
        return transcript.text if transcript else None
    except Exception as e:
        print(f"Transcription error: {e}")
        return None

def extract_text_from_pdf(file_path):
    try:
        text = ""
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ""  # Handle None returns
        return text if text.strip() else None
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return None

def generate_summary(text):
    try:
        # Truncate very long text to prevent timeouts
        truncated_text = text[:100000] if len(text) > 100000 else text
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = """Convert this lecture content into comprehensive Markdown-formatted study notes with the following structure:

```markdown
# Lecture Summary
[Provide 3-4 concise paragraphs covering the core concepts, main arguments, and key conclusions]

## Detailed Notes
### [Topic 1]
- **Key Definitions**:
  - [Term 1]: [Definition]
  - [Term 2]: [Definition]
- **Main Points**:
  - [Point 1 with explanation]
  - [Point 2 with explanation]
- **Examples**:
  - [Example 1]
  - [Example 2]
- **Connections**: [How this relates to other concepts]

### [Topic 2]
[Same structure as above]

## Key Takeaways
- 🔹 [Most important concept 1]
- 🔹 [Most important concept 2]
- 🔹 [Potential exam focus area]

## Study Aids
### Mnemonics
- [Mnemonic device 1]
- [Mnemonic device 2]

### Visual Representation
```mermaid
[Simple Mermaid diagram code when applicable]Formatting Requirements:
1. Use proper Markdown headers (##, ###)
2. **Bold** all key terms and definitions
3. Use emojis sparingly for emphasis (🔹, ❗, ⭐)
4. Include Mermaid diagram syntax where helpful
5. Create clear sections with horizontal rules (---)
6. Mark uncertain areas with [❓]
7. Keep bullet points concise but complete
8. Include timestamp markers if available

Content to analyze:
{content}""".format(content=truncated_text)
        
        response = model.generate_content(prompt)
        
        # Handle different response formats
        if hasattr(response, 'text'):
            return response.text
        elif hasattr(response, 'candidates') and response.candidates:
            return response.candidates[0].content.parts[0].text
        else:
            return "Could not generate summary (unexpected response format)"
            
    except Exception as e:
        print(f"Summary generation error: {e}")
        return f"Summary generation failed: {str(e)}"

def extract_transcript_details(youtube_video_url):
    try:
        # Extract video ID from various YouTube URL formats
        import re
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", youtube_video_url)
        if not match:
            return None
        video_id = match.group(1)
        transcript_text = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = " ".join([i["text"] for i in transcript_text])
        return transcript, video_id
    except Exception as e:
        print(f"Transcript extraction error: {e}")
        return None, None

def generate_youtube_summary(transcript_text):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "You are a YouTube video summarizer. Summarize the transcript below in detailed, clear bullet points (max 250 words):\n\n"
            + transcript_text
        )
        response = model.generate_content(prompt)
        return response.text if hasattr(response, "text") else str(response)
    except Exception as e:
        print(f"Gemini summary error: {e}")
        return "Summary generation failed."

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # File upload processing
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('index'))
            
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('index'))
            
        if file and allowed_file(file.filename):
            try:
                # Secure filename and create temp directory
                filename = secure_filename(file.filename)
                temp_dir = tempfile.mkdtemp()
                temp_path = os.path.join(temp_dir, filename)
                file.save(temp_path)
                
                # Process based on file type
                extension = filename.rsplit('.', 1)[1].lower()
                
                if extension in {'mp3', 'wav', 'mp4'}:
                    text = transcribe_audio(temp_path)
                    source_type = 'Audio/Video File'
                elif extension == 'pdf':
                    text = extract_text_from_pdf(temp_path)
                    source_type = 'PDF Document'
                elif extension == 'txt':
                    with open(temp_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    source_type = 'Text File'
                
                # Clean up
                os.remove(temp_path)
                os.rmdir(temp_dir)
                
                if not text:
                    flash('Error processing file content. Please try another.', 'error')
                    return redirect(url_for('index'))
                    
                summary = generate_summary(text)
                return render_template('results.html', 
                                     original_text=text,
                                     summary=summary,
                                     source_type=source_type)
                    
            except Exception as e:
                print(f"File processing error: {e}")
                # Clean up if temp files exist
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
                if 'temp_dir' in locals() and os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
                flash('Error processing file. Please try another.', 'error')
                return redirect(url_for('index'))
                
        else:
            flash('Invalid file type. Supported formats: MP3, WAV, MP4, PDF, TXT', 'error')
            return redirect(url_for('index'))
    
    return render_template('index.html')

@app.route('/youtube', methods=['GET', 'POST'])
def youtube():
    summary = None
    transcript = None
    video_id = None
    error = None
    if request.method == 'POST':
        youtube_url = request.form.get('youtube_link')
        if not youtube_url:
            error = "Please enter a YouTube URL."
        else:
            transcript, video_id = extract_transcript_details(youtube_url)
            if not transcript:
                error = "Could not extract transcript. The video may not have captions."
            else:
                summary = generate_youtube_summary(transcript)
    return render_template('youtube.html', summary=summary, transcript=transcript, video_id=video_id, error=error)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)