import base64
import logging
import os
import random
import shutil
import string
import time
import traceback
from pathlib import Path
from tempfile import TemporaryDirectory

from flask import Flask, request, redirect, send_file, render_template

from furiganalyse.__main__ import main, SUPPORTED_INPUT_EXTS
from furiganalyse.params import OutputFormat

UPLOAD_FOLDER = '/tmp/furiganalysed_uploads/'
OUTPUT_FOLDER = '/tmp/furiganalysed_downloads/'
app = Flask(__name__, template_folder='./templates')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)
Path(OUTPUT_FOLDER).mkdir(exist_ok=True)


@app.route("/", methods=['GET'])
def get_root():
    return render_upload()


# Upload API
@app.route('/upload-file', methods=['GET', 'POST'])
def get_post_upload_file():
    if request.method == 'GET':
        return render_upload()

    # check if the post request has the file part
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']

    # if user does not select file, browser also
    # submit a empty part without filename
    if file.filename == '':
        return redirect(request.url)

    output_format = OutputFormat(request.form["of"])

    filename = file.filename
    output_filepath = filename_to_output_filepath(filename, output_format)
    path_hash = encode_filepath(output_filepath)

    cleanup_output_folder()

    with TemporaryDirectory(dir=app.config['UPLOAD_FOLDER']) as td:
        tmpfile = os.path.join(td, filename)
        file.save(tmpfile)
        try:
            main(
                tmpfile,
                output_filepath,
                furigana_mode=request.form['furigana_mode'],
                output_format=output_format,
                writing_mode=request.form['writing_mode'],
            )
        except Exception:
            logging.error(f"Error while processing {tmpfile}: {traceback.format_exc()}")
            return redirect('/error-file/' + filename)

    # send file name as parameter to downlad
    return redirect('/download-file/' + path_hash)


@app.route("/error-file/<filename>", methods=['GET'])
def get_error_file(filename):
    return render_template('error.html', value=filename)


# Download API
@app.route("/download-file/<path_hash>", methods=['GET'])
def get_download_file(path_hash):
    return render_template('download.html', value=path_hash)


@app.route('/files/<path_hash>')
def get_files(path_hash):
    file_path = decode_filepath(path_hash)
    if not file_path.startswith(app.config['OUTPUT_FOLDER']):
        return render_template('error.html', value=os.path.basename(file_path))

    attachment_filename = "furiganalysed_" + os.path.basename(file_path)
    return send_file(file_path, as_attachment=True, attachment_filename=attachment_filename)


OUTPUT_FORMAT_TO_EXTENSION = {
    OutputFormat.epub: ".epub",
    OutputFormat.mobi: ".mobi",
    OutputFormat.azw3: ".azw3",
    OutputFormat.many_txt: ".zip",
    OutputFormat.single_txt: ".txt",
    OutputFormat.apkg: ".apkg",
    OutputFormat.html: ".html",
}


def filename_to_output_filepath(filename: str, output_format: OutputFormat) -> str:
    filename_without_ext = os.path.splitext(filename)[0]
    extension = OUTPUT_FORMAT_TO_EXTENSION[output_format]
    output_filename = filename_without_ext + extension
    output_filepath = os.path.join(app.config['OUTPUT_FOLDER'], generate_random_key(12), output_filename)
    Path(output_filepath).parent.mkdir(parents=True)
    return output_filepath


def generate_random_key(length):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))


def encode_filepath(filepath):
    return str(base64.urlsafe_b64encode(filepath.encode("utf-8")), "utf-8")


def decode_filepath(hashed_path):
    return str(base64.urlsafe_b64decode(hashed_path.encode("utf-8")), "utf-8")


def cleanup_output_folder():
    """
    Keep the total size of output folder below a threshold, thrashing from the older files when needed.
    """
    size_threshold = int(100e6)  # 100MB

    output_folder = Path(app.config['OUTPUT_FOLDER'])
    paths = sorted(output_folder.iterdir(), key=os.path.getctime)

    path_and_sizes = []
    total_size = 0
    for path in paths:
        size = sum(f.stat().st_size for f in path.glob('**/*') if f.is_file())
        path_and_sizes.append((path, size))
        total_size += size

    if total_size < size_threshold:
        return
    for path, size in path_and_sizes:
        logging.info(f"Removing {path} to free up space")
        shutil.rmtree(path)
        total_size -= size
        if total_size < size_threshold:
            break


def render_upload():
    return render_template('upload.html', supported_input_exts=','.join(SUPPORTED_INPUT_EXTS))


if __name__ == "__main__":
    app.run(host='0.0.0.0')