import logging
import os
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from furiganalyse.params import OutputFormat, WritingMode
from furiganalyse.parsing import process_html, convert_html_to_txt

# Register XHTML namespace with empty prefix (default namespace)
# This prevents ElementTree from adding 'html:' prefix to all elements when serializing
ET.register_namespace('', 'http://www.w3.org/1999/xhtml')


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
    for css_filepath in Path(unzipped_input_fpath).glob('**/*.css'):
        with open(css_filepath) as fd:
            css_content = fd.read()

        pattern = re.compile(r"(-webkit-writing-mode|-epub-writing-mode|writing-mode):\s*[^;\n]+")
        css_content = pattern.sub(rf"\1: {writing_mode.value}", css_content)

        with open(css_filepath, "w") as fd:
            fd.write(css_content)

    # content.opf has a tag like this: <meta name="primary-writing-mode" content="vertical-rl"/>
    # content_opf_path: Path = Path(unzipped_input_fpath) / "content.opf"
    # if content_opf_path.exists():
    #     from xml.etree import ElementTree as ET
    #     tree = ET.parse(content_opf_path)
    #     # import ipdb; ipdb.set_trace()
    #     x: ET.Element = tree.find(".//{http://www.idpf.org/2007/opf}meta[@name='primary-writing-mode']")
    #     x.attrib["content"] = writing_mode.value
    #     tree.write(content_opf_path, encoding="utf-8")


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