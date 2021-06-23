import xml.etree.ElementTree as ET

import pytest

from furiganalyse.__main__ import process_tree


@pytest.mark.parametrize(
    ("xml_str", "expected_xml_str"),
    [
        (
            '<head><title>世界一やさしい「やりたいこと」の見つけ方　人生のモヤモヤから解放される自己理解メソッド</title></head>',
            '<head><title><ruby>世界一<rt>せかいいち</rt></ruby>やさしい「やりたいこと」の<ruby>見<rt>み</rt></ruby>つけ<ruby>方<rt>かた</rt></ruby>　<ruby>人生<rt>じんせい</rt></ruby>のモヤモヤから<ruby>解放<rt>かいほう</rt></ruby>される<ruby>自己<rt>じこ</rt></ruby><ruby>理解<rt>りかい</rt></ruby>メソッド</title></head>',
        ),
        (
            '<body>はじめに、<ruby>第一<rt>ファースト</rt></ruby>歩。</body>',
            '<body>はじめに、<ruby>第一<rt>ファースト</rt></ruby><ruby>歩<rt>ふ</rt></ruby>。</body>',
        ),
        (
            """
            <body class="p-text">
              <div class="main2">
                <p id="1">
                　1つの成功体験は
                  <a>ハーバード大学。</a>
                  その真ん中を
                  <span>はじめに、第一。</span>
                </p>
                その後で
                <p id="2">No kanji around here<br class="main"/></p>
              </div>
            </body>
            """,
            """
            <body class="p-text">
              <div class="main2">
                <p id="1">1つの<ruby>成功体験<rt>せいこうたいけん</rt></ruby>は<a>ハーバード<ruby>大学<rt>だいがく</rt></ruby>。</a>その<ruby>真<rt>ま</rt></ruby>ん<ruby>中<rt>なか</rt></ruby>を<span>はじめに、<ruby>第一<rt>だいいち</rt></ruby>。</span>
                </p>その<ruby>後<rt>ご</rt></ruby>で<p id="2">No kanji around here<br class="main" /></p>
              </div>
            </body>
            """,
        )
    ]
)
def test_process_tree(xml_str, expected_xml_str):
    template = """
    <?xml version='1.0' encoding='utf-8'?>
    <html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ja" class="hltr">
    {}
    </html>
    """.strip()

    tree = ET.fromstring(template.format(xml_str))

    process_tree(tree)

    expected_tree = ET.fromstring(template.format(expected_xml_str))

    assert ET.tostring(tree, encoding='unicode') == ET.tostring(expected_tree, encoding='unicode')