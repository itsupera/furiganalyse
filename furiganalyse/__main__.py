import logging
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from tempfile import TemporaryDirectory
from typing import Optional, Tuple, List

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


def process_html(inputfile: str, outputfile: Optional[str] = None):
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
        if not p.tag.endswith("rt"):
            logging.debug(f">>> BEFORE {p.tag} > '{p.text}' {list(p)} '{p.tail}'")
            process_head(p)
            process_tail(p, parent_map[p])
            logging.debug(f">>> AFTER  {p.tag} > '{p.text}' {list(p)} '{p.tail}'")

    # Add the namespace to our new elements
    elems = tree.findall('.//{}*')
    for elem in elems:
        elem.tag = namespace + elem.tag


def process_head(elem: ET.Element):
    """
    Process the text that is before the children of the given element.
    """
    if not elem.text or elem.tag.endswith("ruby"):
        return

    text = elem.text.strip()
    if contains_kanji(text):

        head, children, tail = create_parsed_furigana_html(text)

        # Replace the original text by the ruby childs "head"
        elem.text = head

        # Insert the children at the beginning
        for child in reversed(children):
            elem.insert(0, child)


def process_tail(elem: ET.Element, parent_elem: ET.Element):
    """
    Process the text that is before the children of the given element.
    """
    if not elem.tail:
        return

    text = elem.tail.strip()
    if contains_kanji(text):

        head, children, tail = create_parsed_furigana_html(text)

        # Replace the original tail by the rubys "head"
        elem.tail = head

        # Insert the ruby children just after the element
        idx = list(parent_elem).index(elem)
        for child in reversed(children):
            parent_elem.insert(idx + 1, child)


def create_parsed_furigana_html(text: str) -> Tuple[str, List[ET.Element], str]:
    """
    Generate the furigana and return it parsed: "head" text, <ruby> children, "tail" text.
    """
    new_text = create_furigana_html(text)

    # Need to wrap the children <ruby> elements in something to parse them
    try:
        elem = ET.fromstring(f"""<p>{new_text}</p>""")
    except ET.ParseError:
        logging.error(f"XML parsing failed for {new_text}, which was generated from: {text}")
        raise

    # Return the parts that will need to be integrated in the XML tree
    return elem.text, list(elem), elem.tail


kanji_pattern = re.compile(f"[一-龯]")


def contains_kanji(text: str) -> bool:
    return bool(kanji_pattern.search(text))


if __name__ == '__main__':
    typer.run(main)
