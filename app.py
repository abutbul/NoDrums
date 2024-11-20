import os
import shutil
import subprocess
import requests
import yt_dlp as youtube_dl
import logging
import hashlib
import re
from datetime import datetime
from flask import Flask, request, send_from_directory, render_template_string
from werkzeug.utils import secure_filename
from pydub import AudioSegment

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'mp3'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure necessary folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Checks if the given filename has an allowed file extension.
    
    Args:
        filename (str): The name of the file to check.
    
    Returns:
        bool: True if the file has an allowed extension, False otherwise.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def download_file_from_url(url, save_path):
    """Downloads a file from a specified URL and saves it to a given path.
    
    Args:
        url str: The URL of the file to be downloaded.
        save_path str: The local path where the downloaded file will be saved.
    
    Returns:
        bool: True if the file was downloaded and saved successfully; False otherwise.
    """
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        logger.info(f"File downloaded from URL to {save_path}")
        return True
    logger.error(f"Failed to download file from URL: {url}")
    return False

def download_youtube_audio(url, save_path):
    """Download audio from a YouTube video and save it in the specified format.
    
    Args:
        url str: The URL of the YouTube video from which to download audio.
        save_path str: The path (including filename) where the audio file will be saved.
    
    Returns:
        None: This method does not return a value but will log the download status.
    """
    save_path = save_path.rsplit('.', 1)[0]  # Remove the extension if it exists
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': save_path,
        'restrictfilenames': True,
        'noplaylist': True,
        'nocontinue': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        }],
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    save_path += '.wav'
    logger.info(f"YouTube audio downloaded to {save_path}")

def run_command(command):
    """Executes a system command and logs the output and errors.
    
    Args:
        command list: A list of command line arguments to be executed.
    
    Returns:
        None: This method does not return a value. It raises an exception on command failure.
    """
    logger.debug(f"Executing command: {' '.join(command)}")
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        logger.error(f"Command {' '.join(command)} failed with error: {result.stderr.strip()}")
        raise subprocess.CalledProcessError(result.returncode, command, result.stderr.strip())
    logger.info(f"Command {' '.join(command)} succeeded with output: {result.stdout.strip()}")

def calculate_file_hash(file):
    """Calculates the MD5 hash of a given file object.
    
    Args:
        file _io.BufferedReader: A file-like object that supports reading.
    
    Returns:
        str: The hexadecimal representation of the MD5 hash of the file's content.
    """
    hasher = hashlib.md5()
    file.seek(0)
    for chunk in iter(lambda: file.read(4096), b""):
        hasher.update(chunk)
    file.seek(0)
    return hasher.hexdigest()

def get_youtube_slug(url):
    """Extracts the YouTube video ID from the given URL.
    
    Args:
        url str: The YouTube video URL from which to extract the video ID.
    
    Returns:
        str or None: The YouTube video ID if found; otherwise, None.
    """
    match = re.search(r'v=([\w-]+)', url)
    return match.group(1) if match else None

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    """Handles file upload and audio processing via Spleeter and Sox.
    
    This function processes uploaded files or URLs to separate audio stems 
    using the Spleeter library and merges the results into combined audio files 
    using the Sox tool. It verifies file uploads, checks for cached results, 
    and logs status updates throughout the process.
    
    Args:
        request: Flask request object containing form data and uploaded files.
    
    Returns:
        str: Rendered HTML template showing the upload status and processed files 
             or an error message if the process fails.
    """
    status_updates = []
    file_hash = None
    if request.method == 'POST':
        if 'file_submit' in request.form and 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return 'No selected file'
            if file and allowed_file(file.filename):
                file_hash = calculate_file_hash(file)
                filename = f"{file_hash}.mp3"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                logger.info(f"File saved to {file_path}")
                status_updates.append(f"{datetime.now()} - File saved to {file_path}")
            else:
                return 'Invalid file type'
        elif 'url_submit' in request.form and 'url' in request.form:
            url = request.form['url']
            youtube_slug = get_youtube_slug(url)
            if youtube_slug:
                filename = f"{youtube_slug}.wav"
            else:
                filename = hashlib.md5(url.encode()).hexdigest() + '.mp3'
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            if url.endswith('.mp3'):
                if not download_file_from_url(url, file_path):
                    return 'Failed to download file from URL'
                status_updates.append(f"{datetime.now()} - File downloaded from URL to {file_path}")
            else:
                try:
                    download_youtube_audio(url, file_path)
                    file_path = file_path.rsplit('.', 1)[0] + '.wav'  # Update file_path after download
                    status_updates.append(f"{datetime.now()} - YouTube audio downloaded to {file_path}")
                except Exception as e:
                    logger.error(f"Failed to download YouTube audio: {e}")
                    return f'Failed to download YouTube audio: {str(e)}'
        else:
            return 'No file or URL provided'

        # Verify file hash before running Spleeter
        original_hash = request.form.get('file_hash')
        current_hash = calculate_file_hash(open(file_path, 'rb'))
        if original_hash and original_hash != current_hash:
            status_updates.append(f'{datetime.now()} - File upload verification failed. Please try again.')
            logger.error('File upload verification failed. Hash mismatch.')
            return render_template_string(TEMPLATE, status_updates=status_updates, file_hash=file_hash)
        status_updates.append(f'{datetime.now()} - File hash verified: {current_hash}')
        logger.info(f'File hash verified: {current_hash}')

        # Define output base directory using file hash or slug
        output_base_dir = os.path.join(OUTPUT_FOLDER, file_hash if file_hash else youtube_slug)

        # Check if the file has already been processed
        expected_files = ['vocals.wav', 'drums.wav', 'bass.wav', 'other.wav']
        subdirectory = os.path.join(output_base_dir, file_hash if file_hash else youtube_slug)
        if all(os.path.exists(os.path.join(subdirectory, stem)) for stem in expected_files):
            logger.info(f"Using cached output for file {file_hash if file_hash else youtube_slug}")
            status_updates.append(f"{datetime.now()} - Using cached output for file {file_hash if file_hash else youtube_slug}")
        else:
            # Run spleeter to separate stems
            os.makedirs(output_base_dir, exist_ok=True)
            try:
                logger.info(f"Running Spleeter on {file_path} with output to {output_base_dir}")
                status_updates.append(f"{datetime.now()} - Running Spleeter on {file_path}")
                command = [
                    'spleeter',
                    'separate',
                    '-o', os.path.abspath(output_base_dir),
                    '-p', 'spleeter:4stems',
                    os.path.abspath(file_path)
                ]
                # Force model download by setting environment variable
                env = os.environ.copy()
                env['MODEL_PATH'] = ''  # Enforce model download i.e.  env['MODEL_PATH'] = '/root/.config/spleeter/pretrained_models' 
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
                # After Spleeter runs successfully
                if result.returncode != 0:
                    logger.error(f"Command {' '.join(command)} failed with error: {result.stderr.strip()}")
                    raise subprocess.CalledProcessError(result.returncode, command, result.stderr.strip())
                logger.info(f"Command {' '.join(command)} succeeded with output: {result.stdout.strip()}")
                status_updates.append(f"{datetime.now()} - Spleeter separation complete.")
            except subprocess.CalledProcessError as e:
                return f"Spleeter failed with error: {e}"

        # Log files in output directory before verification
        logger.info(f"Listing files in output directory {output_base_dir}")
        for root, dirs, files in os.walk(output_base_dir):
            for file in files:
                logger.info(f"Found file: {os.path.join(root, file)}")

        # Verify if Spleeter output files exist
        missing_files = []
        invalid_files = []
        for expected_file in expected_files:
            expected_file_path = os.path.join(subdirectory, expected_file)
            if not os.path.exists(expected_file_path):
                missing_files.append(expected_file)
            else:
                try:
                    AudioSegment.from_file(expected_file_path)
                except Exception as e:
                    logger.error(f"Invalid audio file for {expected_file}: {e}")
                    invalid_files.append(expected_file)
        if missing_files:
            logger.error(f"Missing output files: {missing_files}")
            status_updates.append(f"{datetime.now()} - Error: Missing output files: {', '.join(missing_files)}")
            return render_template_string(TEMPLATE, status_updates=status_updates, file_hash=file_hash)
        if invalid_files:
            logger.error(f"Invalid audio files: {invalid_files}")
            status_updates.append(f"{datetime.now()} - Error: Invalid audio files: {', '.join(invalid_files)}")
            return render_template_string(TEMPLATE, status_updates=status_updates, file_hash=file_hash)

        # Create a merged file using Sox
        merged_file = os.path.join(output_base_dir, 'merged.mp3')
        if not os.path.exists(merged_file):
            try:
                logger.info(f"Running Sox to merge files into {merged_file}")
                status_updates.append(f"{datetime.now()} - Running Sox to merge files.")
                run_command(['sox', '-m', os.path.join(subdirectory, 'bass.wav'),
                             os.path.join(subdirectory, 'vocals.wav'),
                             os.path.join(subdirectory, 'other.wav'), '-C', '192', merged_file, 'gain', '5'])
                status_updates.append(f"{datetime.now()} - Sox merging complete.")
            except subprocess.CalledProcessError as e:
                return f"Sox failed with error: {e}"

        # Create a merged file without vocals using Sox
        merged_no_vocals_file = os.path.join(output_base_dir, 'merged_no_vocals.mp3')
        if not os.path.exists(merged_no_vocals_file):
            try:
                logger.info(f"Running Sox to merge files into {merged_no_vocals_file}")
                status_updates.append(f"{datetime.now()} - Running Sox to merge files without vocals.")
                run_command(['sox', '-m', os.path.join(subdirectory, 'bass.wav'),
                             os.path.join(subdirectory, 'drums.wav'),
                             os.path.join(subdirectory, 'other.wav'), '-C', '192', merged_no_vocals_file, 'gain', '5'])
                status_updates.append(f"{datetime.now()} - Sox merging without vocals complete.")
            except subprocess.CalledProcessError as e:
                return f"Sox failed with error: {e}"

        return render_template_string(TEMPLATE, original=filename, output_files=expected_files, merged_file=merged_file, merged_no_vocals_file=merged_no_vocals_file, status_updates=status_updates, output_identifier=(file_hash if file_hash else youtube_slug))
    return render_template_string(TEMPLATE)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Handles the retrieval of an uploaded file from the server's specified upload folder.
    
    Args:
        filename str: The name of the file to be retrieved.
    
    Returns:
        flask.Response: A file response object that sends the requested file to the client.
    """
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/output/<path:filename>')
def output_file(filename):
    """Sends a file from the specified output directory.
    
    Args:
        filename str: The name of the file to be sent.
    
    Returns:
        Response: The response object that represents the file being sent to the client.
    """
    return send_from_directory(OUTPUT_FOLDER, filename)

TEMPLATE = '''
<!doctype html>
<title>Audio Processing</title>
<h1>Upload an MP3 file or provide a URL</h1>
<form method=post enctype=multipart/form-data>
  <input type=file name=file>
  <br><br>
  <input type=submit value="Upload File" name="file_submit">
  <br><br>
  <label for="url">or provide a URL:</label>
  <input type=text name=url>
  <br><br>
  <input type=submit value="Upload URL" name="url_submit">
  <input type=hidden name="file_hash" id="file_hash">
</form>
<script>
  const fileInput = document.querySelector('input[type="file"]');
  fileInput.addEventListener('change', async () => {
    const file = fileInput.files[0];
    if (file) {
      const hashBuffer = await crypto.subtle.digest('MD5', await file.arrayBuffer());
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
      document.getElementById('file_hash').value = hashHex;
    }
  });
</script>
{% if file_hash %}
  <h2>File Hash:</h2>
  <p>{{ file_hash }}</p>
{% endif %}
{% if original %}
  <h2>Original File:</h2>
  <audio controls>
    <source src="{{ url_for('uploaded_file', filename=original) }}" type="audio/mpeg">
  </audio>
  <h2>Separated Stems:</h2>
  {% for name in output_files %}
    <h3>{{ name.split('.')[0].capitalize() }}</h3>
    <audio controls>
      <source src="{{ url_for('output_file', filename=output_identifier ~ '/' ~ output_identifier ~ '/' ~ name) }}" type="audio/wav">
    </audio>
  {% endfor %}
  <h2>Merged File:</h2>
  <audio controls>
    <source src="{{ url_for('output_file', filename=output_identifier ~ '/merged.mp3') }}" type="audio/mpeg">
  </audio>
  <a href="{{ url_for('output_file', filename=output_identifier ~ '/merged.mp3') }}" download>Download Merged File</a>
  <h2>Merged File Without Vocals:</h2>
  <audio controls>
    <source src="{{ url_for('output_file', filename=output_identifier ~ '/merged_no_vocals.mp3') }}" type="audio/mpeg">
  </audio>
  <a href="{{ url_for('output_file', filename=output_identifier ~ '/merged_no_vocals.mp3') }}" download>Download Merged File Without Vocals</a>
{% endif %}
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

