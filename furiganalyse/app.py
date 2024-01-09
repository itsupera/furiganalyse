import asyncio
import base64
import logging
import os
import random
import shutil
import string
import traceback
from concurrent.futures.process import ProcessPoolExecutor
from pathlib import Path
from typing import Dict
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, Form, FastAPI, Request, status, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

from furiganalyse.__main__ import main, SUPPORTED_INPUT_EXTS
from furiganalyse.params import OutputFormat, FuriganaMode, WritingMode


class Job(BaseModel):
    uid: UUID = Field(default_factory=uuid4)
    status: str = "in_progress"
    result: str = None


jobs: Dict[UUID, Job] = {}


templates = Jinja2Templates(directory="./furiganalyse/templates")
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[""],
    allow_credentials=True,
    allow_methods=[""],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

OUTPUT_FOLDER = '/tmp/furiganalysed/'
Path(OUTPUT_FOLDER).mkdir(exist_ok=True)


@app.get("/", response_class=HTMLResponse)
def get_root(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request, "supported_input_exts": SUPPORTED_INPUT_EXTS})


@app.post("/submit")
async def task_handler(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    furigana_mode: str = Form(),
    writing_mode: str = Form(),
    of: str = Form(),
    redirect: bool = Form(default=True),
):
    new_task = Job()
    jobs[new_task.uid] = new_task

    # Free up some space if necessary
    cleanup_output_folder()

    # Write uploaded file to a temporary file
    task_folder = os.path.join(OUTPUT_FOLDER, str(new_task.uid))
    Path(task_folder).mkdir(exist_ok=True)
    tmpfile = os.path.join(task_folder, file.filename)
    contents = file.file.read()
    with open(tmpfile, 'wb') as f:
        f.write(contents)

    background_tasks.add_task(
        start_furiganalyse_task, new_task.uid, task_folder, file.filename, of, furigana_mode, writing_mode
    )

    if redirect:
        return RedirectResponse(f"/jobs/{new_task.uid}", status_code=status.HTTP_302_FOUND)
    else:
        return {"uid": new_task.uid}


@app.get("/jobs/{uid}", response_class=HTMLResponse)
def get_download(request: Request, uid: UUID):
    return templates.TemplateResponse("download.html", {"request": request, "uid": uid})


def furiganalyse_task(
    task_folder: Path,
    filename: str,
    output_format: str,
    furigana_mode: str,
    writing_mode: str
) -> str:
    input_filepath = os.path.join(task_folder, filename)
    output_filename = generate_output_filename(filename, output_format)
    output_filepath = os.path.join(task_folder, output_filename)
    path_hash = encode_filepath(output_filepath)

    try:
        main(
            input_filepath,
            output_filepath,
            furigana_mode=FuriganaMode(furigana_mode),
            output_format=OutputFormat(output_format),
            writing_mode=WritingMode(writing_mode),
        )
    except Exception:
        logging.error(f"Error while processing {input_filepath}: {traceback.format_exc()}")
        raise

    return path_hash


@app.get("/jobs/{uid}/status")
async def status_handler(uid: UUID):
    job = jobs.get(uid)
    if not job:
        return Response("Uid not found!", status_code=404)
    return jobs[uid]


@app.get('/jobs/{uid}/file')
def get_file(uid: UUID):
    job = jobs.get(uid)
    if not job:
        return Response("Uid not found!", status_code=404)

    if job.status != "complete":
        return Response("Job not completed yet!", status_code=400)

    if not job.result:
        return Response("Something went wrong!", status_code=500)

    path_hash = job.result
    file_path = decode_filepath(path_hash)
    filename = os.path.basename(file_path)
    return FileResponse(path=file_path, filename=filename)


@app.on_event("startup")
async def startup_event():
    app.state.executor = ProcessPoolExecutor()


@app.on_event("shutdown")
async def on_shutdown():
    app.state.executor.shutdown()


OUTPUT_FORMAT_TO_EXTENSION = {
    OutputFormat.epub: ".epub",
    OutputFormat.mobi: ".mobi",
    OutputFormat.azw3: ".azw3",
    OutputFormat.many_txt: ".zip",
    OutputFormat.single_txt: ".txt",
    OutputFormat.apkg: ".apkg",
    OutputFormat.html: ".html",
}


def generate_output_filename(input_filename: str, output_format: OutputFormat) -> str:
    filename_without_ext = os.path.splitext(input_filename)[0]
    extension = OUTPUT_FORMAT_TO_EXTENSION[output_format]
    output_filename = "furiganalysed_" + filename_without_ext + extension
    return output_filename

def generate_random_key(length):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))


def encode_filepath(filepath):
    return str(base64.urlsafe_b64encode(filepath.encode("utf-8")), "utf-8")


def decode_filepath(hashed_path):
    return str(base64.urlsafe_b64decode(hashed_path.encode("utf-8")), "utf-8")


def cleanup_output_folder(force: bool = False):
    """
    Keep the total size of output folder below a threshold, thrashing from the older files when needed.
    """
    size_threshold = int(100e6)  # 100MB

    output_folder = Path(OUTPUT_FOLDER)
    paths = sorted(output_folder.iterdir(), key=os.path.getctime)

    path_and_sizes = []
    total_size = 0
    for path in paths:
        size = sum(f.stat().st_size for f in path.glob('**/*') if f.is_file())
        path_and_sizes.append((path, size))
        total_size += size

    if total_size < size_threshold and not force:
        return

    for path, size in path_and_sizes:
        logging.info(f"Removing {path} to free up space")

        uid = UUID(os.path.basename(path))
        if uid in jobs:
            logging.info(f"Deleting associated job {uid}")
            del jobs[uid]

        shutil.rmtree(path)
        total_size -= size
        if total_size < size_threshold and not force:
            break


async def run_in_process(fn, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(app.state.executor, fn, *args)  # wait and return result


async def start_furiganalyse_task(uid: UUID, *args) -> None:
    try:
        jobs[uid].result = await run_in_process(furiganalyse_task, *args)
        jobs[uid].status = "complete"
    except:
        logging.error(f"Error occured for job {uid}")
        jobs[uid].status = "error"