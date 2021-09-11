import logging
import os
import zipfile
from typing import Iterator


def write_txt_archive(unzipped_input_fpath: str, outputfile: str):
    """
    Only keep the converted txt files within the archive.
    """
    with zipfile.ZipFile(outputfile, 'w') as zip_out:
        for folder_name, _, filenames in os.walk(unzipped_input_fpath):
            for filename in filenames:
                extension = os.path.splitext(filename)[1]
                if extension == ".txt":
                    rel_dir = os.path.relpath(folder_name, unzipped_input_fpath)
                    rel_file = os.path.join(rel_dir, filename)
                    file_path = os.path.join(folder_name, filename)
                    # Add file to zip
                    zip_out.write(file_path, rel_file)
                    logging.info(f"    Adding {rel_file}")


def iter_txt_lines(unzipped_input_fpath: str) -> Iterator[str]:
    for root, _, files in sorted(os.walk(unzipped_input_fpath)):
        for file in sorted(files):
            if os.path.splitext(file)[1] == ".txt":
                filepath = os.path.join(root, file)
                with open(filepath) as fd:
                    for line in fd:
                        yield line


def concat_txt_files(unzipped_input_fpath: str, outputfile: str):
    with open(outputfile, "w") as fd:
        for line in iter_txt_lines(unzipped_input_fpath):
            fd.write(line)