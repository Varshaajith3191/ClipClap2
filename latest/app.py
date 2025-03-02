from flask import Flask, render_template, request, send_file, after_this_request
from moviepy.editor import VideoFileClip
import os
from werkzeug.utils import secure_filename
import whisper
from transformers import pipeline
from fpdf import FPDF
from docx import Document
import tempfile
from googletrans import Translator

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
# new line added

# Load Whisper model
model = whisper.load_model("base")
summarizer = pipeline("summarization")
translator = Translator()

# Function to save as PDF
def save_as_pdf(text, filename):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, text)
    pdf.output(filename)

# Function to save as DOCX
def save_as_docx(text, filename):
    doc = Document()
    doc.add_paragraph(text)
    doc.save(filename)

# Function to chunk text for timestamps
def chunk_text(text, max_words=100):
    words = text.split()
    chunks = []
    current_chunk = []
    timestamp = 0
    interval = 10

    for i, word in enumerate(words):
        current_chunk.append(word)
        if len(current_chunk) >= max_words or i == len(words) - 1:
            chunk_text = ' '.join(current_chunk)
            chunks.append((timestamp, chunk_text))
            timestamp += interval
            current_chunk = []

    return chunks

# Function to chunk summary
def chunk_summary(summary, max_words=40):
    words = summary.split()
    chunks = []
    current_chunk = []
    timestamp = 0
    interval = 30

    for i, word in enumerate(words):
        current_chunk.append(word)
        if len(current_chunk) >= max_words or i == len(words) - 1:
            chunk_text = ' '.join(current_chunk)
            chunks.append((timestamp, chunk_text))
            timestamp += interval
            current_chunk = []

    return chunks

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Video Summary Generator</title>
    </head>
    <body>
        <h1>Video Summary Generator</h1>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" required><br><br>
            <label for="max_words">Max Words in Summary:</label>
            <input type="number" name="max_words" value="130"><br><br>
            <button type="submit">Upload and Generate Summary</button>
        </form>
    </body>
    </html>
    '''

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return "No file part"

    file = request.files['file']

    if file.filename == '':
        return "No selected file"

    if file:
        max_words = int(request.form['max_words'])
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Extract audio from video
        video = VideoFileClip(filepath)
        audio_path = filepath.replace('.mp4', '.mp3')
        video.audio.write_audiofile(audio_path)

        # Transcribe audio
        result = model.transcribe(audio_path)
        transcript = result['text']

        # Generate summary
        summary = summarizer(transcript, max_length=max_words, min_length=30, do_sample=False)[0]['summary_text']

        # Chunking for timestamps
        chunks = chunk_text(transcript)
        summary_chunks = chunk_summary(summary)

        # HTML output
        html_output = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Video Summary Result</title>
        </head>
        <body>
            <h1>Uploaded Video</h1>
            <video width="640" height="360" controls id="videoPlayer">
                <source src="/{filepath}" type="video/mp4">
                Your browser does not support the video tag.
            </video>

            <h1>Extracted Audio</h1>
            <audio controls>
                <source src="/{audio_path}" type="audio/mpeg">
                Your browser does not support the audio tag.
            </audio>

            <h1>Summary</h1>
            <p><b>Summary:</b></p>
            <p>{summary}</p>

            <h1>Summary with Timestamps</h1>
        '''

        for timestamp, chunk in summary_chunks:
            minutes = timestamp // 60
            seconds = timestamp % 60
            html_output += f'<p><b><a href="#" onclick="seekVideo({timestamp})">{minutes:02d}:{seconds:02d}</a></b> - {chunk}</p>'

        html_output += '<hr><h1>Text with Timestamps</h1>'

        for timestamp, chunk in chunks:
            minutes = timestamp // 60
            seconds = timestamp % 60
            html_output += f'<p><b><a href="#" onclick="seekVideo({timestamp})">{minutes:02d}:{seconds:02d}</a></b> - {chunk}</p>'

        # Add Export Buttons
        html_output += '''
        <hr>
        <h2>Export Summary</h2>
        <a href="/export/pdf" target="_blank"><button>Download PDF</button></a>
        <a href="/export/docx" target="_blank"><button>Download DOCX</button></a>

        <h2>Translate Summary</h2>
        <form action="/translate" method="post">
            <input type="hidden" name="summary" value="''' + summary + '''">
            <select name="language">
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
                <option value="hi">Hindi</option>
            </select>
            <button type="submit">Translate</button>
        </form>

        <script>
            function seekVideo(time) {
                var video = document.getElementById('videoPlayer');
                video.currentTime = time;
                video.play();
            }
        </script>
        </body>
        </html>
        '''

        return html_output

@app.route('/export/<format>', methods=['GET'])
def export_summary(format):
    summary_text = request.args.get('summary')
    file_format = format.lower()
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, f'summary.{file_format}')
    
    if file_format == 'pdf' or file_format == "xm":
        save_as_pdf(summary_text, file_path)
    elif file_format == 'docx':
        save_as_docx(summary_text, file_path)

    @after_this_request
    def cleanup(response):
        os.remove(file_path)
        os.rmdir(temp_dir)
        return response

    return send_file(file_path, as_attachment=True, download_name=f'summary.{file_format}')

@app.route('/translate', methods=['POST'])
def translate():
    summary_text = request.form['summary']
    language = request.form['language']
    translated_text = translator.translate(summary_text, dest=language).text
    
    return f'''
    <h2>Translated Summary</h2>
    <p>{translated_text}</p>
    <br><a href="/">Go Back</a>
    '''

if __name__ == '__main__':
    app.run(debug=True)
