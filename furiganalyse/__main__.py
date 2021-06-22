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
    parent_map = dict((c, p) for p in tree.iter() for c in p)

    namespace = "{http://www.w3.org/1999/xhtml}"
    ps = tree.findall(f'.//{namespace}*')
    for p in ps:
        process_text(p)
        process_tail(p, parent_map[p])

    # Add the namespace to our new elements
    elems = tree.findall('.//{}*')
    for elem in elems:
        elem.tag = namespace + elem.tag


def process_text(p: ET.Element):
    if not p.text:
        return

    text = p.text.strip()
    if contains_kanji(text):
        new_text = create_furigana_html(text)

        # Need to wrap the child <ruby> elements in something before we copy them
        try:
            new_elem = ET.fromstring(f"""<p>{new_text}</p>""")
        except ET.ParseError:
            logging.error(f"XML parsing failed for {new_text}, which was generated from: {text}")
            raise

        # Replace the original text by the ruby childs "head"
        p.text = new_elem.text

        new_childs = list(new_elem)
        for new_child in reversed(new_childs):
            p.insert(0, new_child)


def process_tail(p: ET.Element, parent_elem: ET.Element):
    if not p.tail:
        return

    text = p.tail.strip()
    if contains_kanji(text):
        processed_text = create_furigana_html(text)

        # Need to wrap the child <ruby> elements in something before we copy them
        try:
            new_elem = ET.fromstring(f"""<p>{processed_text}</p>""")
        except ET.ParseError:
            logging.error(f"XML parsing failed for {processed_text}, which was generated from: {text}")
            raise

        # Replace the original tail by the rubys "head"
        p.tail = new_elem.text

        # Insert the ruby childs just after the element
        idx = list(parent_elem).index(p)
        new_childs = list(new_elem)
        for new_child in reversed(new_childs):
            parent_elem.insert(idx + 1, new_child)


kanji_pattern = re.compile(f"[一-龯]")


def contains_kanji(text: str) -> bool:
    return bool(kanji_pattern.search(text))


if __name__ == '__main__':
    typer.run(main)
