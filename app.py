import os
import tempfile
from flask import Flask, render_template, request, redirect, url_for, flash
import google.generativeai as genai
import assemblyai as aai
from pytube import YouTube
from PyPDF2 import PdfReader
from config import GEMINI_API_KEY, ASSEMBLYAI_API_KEY
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24)  # More secure random key
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB upload limit

# Configure APIs
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

def get_youtube_transcript(video_url):
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Initialize YouTube object with better error handling
        try:
            yt = YouTube(video_url, 
                        use_oauth=False,
                        allow_oauth_cache=True)
        except Exception as e:
            print(f"YouTube initialization error: {e}")
            raise Exception("Invalid YouTube URL or video not available")

        # Check video availability
        if yt.age_restricted:
            raise Exception("Age-restricted videos cannot be processed")
            
        # Get best audio stream
        audio_stream = yt.streams.filter(only_audio=True).order_by('abr').last()
        if not audio_stream:
            raise Exception("No audio stream available for this video")
            
        # Download audio to temporary file
        temp_path = os.path.join(temp_dir, "audio.mp4")
        audio_stream.download(output_path=temp_dir, filename="audio.mp4")
        
        # Verify download
        if not os.path.exists(temp_path):
            raise Exception("Failed to download audio")
            
        # Transcribe using AssemblyAI
        text = transcribe_audio(temp_path)
        
        # Clean up
        os.remove(temp_path)
        os.rmdir(temp_dir)
        
        return text
        
    except Exception as e:
        print(f"YouTube processing error: {str(e)}")
        # Clean up if temp files exist
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, filename))
            os.rmdir(temp_dir)
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

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # YouTube URL processing
        if 'video_url' in request.form and request.form['video_url']:
            video_url = request.form['video_url'].strip()
            if not video_url.startswith(('http://', 'https://')):
                flash('Please enter a valid URL', 'error')
                return redirect(url_for('index'))
                
            text = get_youtube_transcript(video_url)
            if not text:
                flash('Error processing YouTube video. Please try another.', 'error')
                return redirect(url_for('index'))
                
            summary = generate_summary(text)
            return render_template('results.html', 
                               original_text=text,
                               summary=summary,
                               source_type='YouTube Video')
        
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)