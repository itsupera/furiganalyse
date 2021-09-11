import logging
import os
import re
import zipfile

from furiganalyse.params import OutputFormat, WritingMode
from furiganalyse.parsing import process_html, convert_html_to_txt


def process_epub_file(unzipped_input_fpath, mode, writing_mode, output_format):
    if writing_mode is not None:
        update_writing_mode(unzipped_input_fpath, writing_mode)

    for root, _, files in os.walk(unzipped_input_fpath):
        for file in files:
            if os.path.splitext(file)[1] in {".html", ".xhtml"}:
                logging.info(f"    Processing {file}")
                html_filepath = os.path.join(root, file)
                tree = process_html(html_filepath, mode)
                if output_format in {OutputFormat.many_txt, OutputFormat.single_txt, OutputFormat.apkg}:
                    txt_outputfile = os.path.splitext(html_filepath)[0] + '.txt'
                    convert_html_to_txt(tree, txt_outputfile)
                else:
                    tree.write(html_filepath, encoding="utf-8")


def update_writing_mode(unzipped_input_fpath: str, writing_mode: WritingMode):
    css_filepath = os.path.join(unzipped_input_fpath, "stylesheet.css")
    with open(css_filepath) as fd:
        css_content = fd.read()

    pattern = re.compile(r"-webkit-writing-mode: [^;\n]+")
    css_content = pattern.sub(f"-webkit-writing-mode: {writing_mode}", css_content)

    with open(css_filepath, "w") as fd:
        fd.write(css_content)


def write_epub_archive(unzipped_input_fpath: str, outputfile: str):
    """
    Write the modified extracted EPUB archive to a new archive file.
    """
    with zipfile.ZipFile(outputfile, 'w') as zip_out:
        for folder_name, _, filenames in os.walk(unzipped_input_fpath):
            for filename in filenames:
                rel_dir = os.path.relpath(folder_name, unzipped_input_fpath)
                rel_file = os.path.join(rel_dir, filename)
                file_path = os.path.join(folder_name, filename)
                # Add file to zip
                zip_out.write(file_path, rel_file)
                logging.info(f"    Adding {rel_file}")