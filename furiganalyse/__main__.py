import logging
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from tempfile import TemporaryDirectory

import typer
from furigana.furigana import create_furigana_html

logging.basicConfig(level=logging.INFO)


def main(inputfile: str, outputfile: str):
    with TemporaryDirectory() as td:
        unzipped_input_fpath = os.path.join(td, "unzipped")

        logging.info("Extracting the archive ...")
        with zipfile.ZipFile(inputfile, 'r') as zip_ref:
            zip_ref.extractall(unzipped_input_fpath)

        logging.info("Processing the files ...")
        for root, _, files in os.walk(unzipped_input_fpath):
            for file in files:
                if file.lower().split('.')[-1] in {"html", "xhtml"}:
                    logging.info(f"    Processing {file}")
                    html_filepath = os.path.join(root, file)
                    process_html(html_filepath)

        logging.info("Creating the archive ...")
        with zipfile.ZipFile(outputfile, 'w') as zip_out:
            for folder_name, _, filenames in os.walk(unzipped_input_fpath):
                for filename in filenames:
                    rel_dir = os.path.relpath(folder_name, unzipped_input_fpath)
                    rel_file = os.path.join(rel_dir, filename)
                    file_path = os.path.join(folder_name, filename)
                    # Add file to zip
                    zip_out.write(file_path, rel_file)
                    logging.info(f"    Adding {rel_file}")


def process_html(inputfile: str, outputfile = None):
    tree = ET.parse(inputfile)
    process_tree(tree)

    if not outputfile:
        outputfile = inputfile

    tree.write(outputfile)


def process_tree(tree: ET.ElementTree):
    # parent_map = dict((c, p) for p in tree.iter() for c in p)

    # TODO also replace in <title> elems
    namespace = "{http://www.w3.org/1999/xhtml}"
    ps = tree.findall(f'.//{namespace}*')
    for p in ps:
        if not p.text:
            continue
        text = p.text.strip()
        if contains_kanji(text):
            new_text = create_furigana_html(text)

            # Need to wrap the child <ruby> elements in something before we copy them
            try:
                new_elem = ET.fromstring(f"""<p>{new_text}</p>""")
            except ET.ParseError:
                logging.error(f"XML parsing failed for {new_text}, which was generated from: {text}")
                raise

            new_childs = list(new_elem)
            for new_child in reversed(new_childs):
                p.insert(0, new_child)

            # Remove the original text, as it was replaced by the <ruby> childs
            p.text = None

    # Add the namespace to our new elements
    elems = tree.findall('.//{}*')
    for elem in elems:
        elem.tag = namespace + elem.tag


kanji_pattern = re.compile(f"[一-龯]")


def contains_kanji(text: str) -> bool:
    return bool(kanji_pattern.search(text))


if __name__ == '__main__':
    typer.run(main)
