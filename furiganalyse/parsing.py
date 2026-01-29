import logging
import re
from typing import Tuple, List, Iterable, Optional, Set
from xml.etree import ElementTree as ET

from furigana.furigana import create_furigana_html

from furiganalyse.params import FuriganaMode

NAMESPACE = "{http://www.w3.org/1999/xhtml}"


def process_html(
    inputfile: str, mode: FuriganaMode, exclude_words: Optional[Set[str]] = None
) -> ET.ElementTree:
    tree = ET.parse(inputfile)
    process_tree(tree, mode, exclude_words)
    return tree


def process_tree(
    tree: ET.ElementTree, mode: FuriganaMode, exclude_words: Optional[Set[str]] = None
):
    parent_map = dict((c, p) for p in tree.iter() for c in p)

    if mode in {"remove", "replace"}:
        remove_existing_furigana(tree, parent_map)

    if mode in {"add", "replace"}:
        ps = tree.findall(f'.//{NAMESPACE}*')
        for p in ps:
            # Exclude ruby related tags, we don't want to override them (unless we have removed them before)
            if not inside_ruby_subtag(p, parent_map):
                logging.debug(f">>> BEFORE {p.tag} > '{p.text}' {list(p)} '{p.tail}'")
                process_head(p, exclude_words)
                process_tail(p, parent_map[p], exclude_words)
                logging.debug(f">>> AFTER  {p.tag} > '{p.text}' {list(p)} '{p.tail}'")

        # Add the namespace to our new elements
        elems = tree.findall('.//{}*')
        for elem in elems:
            elem.tag = NAMESPACE + elem.tag


def inside_ruby_subtag(elem: ET.Element, parent_map):
    """
    Returns True if any of the ascendant tags is a ruby subtag (<rt>, <rb> or <rp>)
    """
    while elem is not None:
        if any((elem.tag.endswith(tag) for tag in {"rt", "rb", "rp"})):
            return True
        elem = parent_map.get(elem)
    return False


def remove_existing_furigana(tree: ET.ElementTree, parent_map: dict):
    """
    Replace all existing ruby elements by their text, e.g., <ruby>X<rt>Y</rt></ruby> becomes X.
    """
    elems = tree.findall(f'.//{NAMESPACE}ruby')
    for elem in elems:
        # Remove all the <rt> children, e.g., the readings, but keep the text from other childs
        childs_text = []
        for child in list(elem):
            if not child.tag.endswith("rt") and not child.tag.endswith("rp"):
                text = (child.text or "") + (child.tail or "")
            else:
                text = child.tail or ""
            childs_text.append(text)
            elem.remove(child)

        # Replacing the node the its text, childs text and tail
        new_text = (elem.text or "") + "".join(childs_text) + (elem.tail or "")

        parent_elem = parent_map[elem]

        # Find the previous child to append our new text to it
        idx = list(parent_elem).index(elem)
        if idx == 0:
            # If our element was the first child, append to parent node's text
            parent_elem.text = (parent_elem.text or "") + new_text
        else:
            # Otherwise, append to the tail of previous children
            previous_elem = parent_elem[idx - 1]
            previous_elem.tail = (previous_elem.tail or "") + new_text

        # Finally, remove our ruby element from its parent
        parent_elem.remove(elem)


def process_head(elem: ET.Element, exclude_words: Optional[Set[str]] = None):
    """
    Process the text that is before the children of the given element.
    """
    if not elem.text or elem.tag.endswith("ruby"):
        return

    text = elem.text.strip()
    if contains_kanji(text):

        head, children, tail = create_parsed_furigana_html(text, exclude_words)

        # Replace the original text by the ruby childs "head"
        elem.text = head

        # Insert the children at the beginning
        for child in reversed(children):
            elem.insert(0, child)


def process_tail(
    elem: ET.Element, parent_elem: ET.Element, exclude_words: Optional[Set[str]] = None
):
    """
    Process the text that is before the children of the given element.
    """
    if not elem.tail:
        return

    text = elem.tail.strip()
    if contains_kanji(text):

        head, children, tail = create_parsed_furigana_html(text, exclude_words)

        # Replace the original tail by the rubys "head"
        elem.tail = head

        # Insert the ruby children just after the element
        idx = list(parent_elem).index(elem)
        for child in reversed(children):
            parent_elem.insert(idx + 1, child)


def create_parsed_furigana_html(
    text: str, exclude_words: Optional[Set[str]] = None
) -> Tuple[str, List[ET.Element], str]:
    """
    Generate the furigana and return it parsed: "head" text, <ruby> children, "tail" text.
    """
    try:
        new_text = create_furigana_html(text, exclude_words=exclude_words)
    except Exception:
        logging.warning("Something wrong happened when retrieving furigana for '%s'", text)
        new_text = text

    # Need to wrap the children <ruby> elements in something to parse them
    try:
        elem = ET.fromstring(f"""<p>{new_text}</p>""")
    except ET.ParseError:
        logging.error(f"XML parsing failed for {new_text}, which was generated from: {text}")
        raise

    # Return the parts that will need to be integrated in the XML tree
    return elem.text, list(elem), elem.tail


kanji_pattern = re.compile("[一-龯]")


def contains_kanji(text: str) -> bool:
    return bool(kanji_pattern.search(text))


def convert_html_to_txt(tree, outputfile):
    with open(outputfile, "w") as fd:
        for line in convert_html_to_txt_lines(tree):
            fd.write(line)


def convert_html_to_txt_lines(tree) -> Iterable[str]:
    rts = tree.findall(f'.//{NAMESPACE}rt')
    for rt in rts:
        rt.text = "(" + (rt.text or "")
        rt.tail = (rt.tail or "") + ")"

    ps = tree.findall(f'.//{NAMESPACE}p')
    for p in ps:
        yield ET.tostring(p, encoding="utf-8", method="text").decode("utf-8")