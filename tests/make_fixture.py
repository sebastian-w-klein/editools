"""Generate a small proof PDF containing every case the audit has to catch.

The lines are drawn one at a time so the line endings are exactly where the
test expects them — a real proof's breaks come from the typesetter, and this
stands in for that.  Cases are drawn from the ruleset's own examples and from
the misses that prompted it.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas

RUNNING_HEAD = "S WA N S"

#: (line, following line) pairs.  The first ends in the break under test.
PAGES: list[list[str]] = [
    [
        "It was a cold morning and she stood at the butch-",
        "er's counter, waiting for the parcel to be wrapped",
        "in paper. The garden was full of cher-",
        "ries—or so the neighbours had always insisted,",
        "though nobody had picked one. She sat down cross-",
        "legged on the step and considered the fold-",
        "up chair her father had left leaning by the door.",
    ],
    [
        "He had been a photo-",
        "grapher once, in the years before Ply-",
        "mouth, and he spoke a careful sort of Eng-",
        "lish that no one there had ever quite trusted.",
        "Whatever co-",
        "meth after, he would say, cometh slowly.",
        "Her mother's name was Mar-",
        "volene, and the letters were addressed to Marvol-",
        "ene in a hand nobody recognised.",
    ],
    [
        "The house had a dis-",
        "pleasure about it, and a displea-",
        "sure in the garden too, a poverty-",
        "stricken look that no amount of paint would lift.",
        "She had read about it at www.exam-",
        "ple.com late one evening, and again in a pov-",
        "erty-stricken pamphlet from the parish council.",
        "There was a sense of encroachment—power-",
        "ful, unhurried—that she could not name.",
        "The word she wanted was dépay-",
        "sement, which nobody in the town could spell.",
    ],
    [
        "Her grandmother had been named for Elizabeth",
        "II, and her grandfather for Sammy Davis",
        "Jr., which everybody agreed was a great deal",
        "to carry. On the shelf were the collected W.",
        "H. Auden and a paperback of Wordswor-",
        "th that had lost its cover years before.",
        "The patrons—-",
        "and there were many—had long since gone.",
    ],
]

ITALIC_WORDS = {"dépay-", "sement,"}


def build(path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path), pagesize=A5)
    width, height = A5

    for page_number, lines in enumerate(PAGES, start=1):
        pdf.setFont("Times-Roman", 8)
        pdf.drawCentredString(width / 2, height - 40, RUNNING_HEAD)

        y = height - 70
        for line in lines:
            x = 50
            for word in line.split(" "):
                font = "Times-Italic" if word in ITALIC_WORDS else "Times-Roman"
                pdf.setFont(font, 11)
                pdf.drawString(x, y, word)
                x += pdf.stringWidth(word + " ", font, 11)
            y -= 18

        pdf.setFont("Times-Roman", 9)
        pdf.drawCentredString(width / 2, 35, str(page_number))
        pdf.showPage()

    pdf.save()
    return path


# --------------------------------------------------------------------------
# A second proof, for words divided across a page turn.
# --------------------------------------------------------------------------

#: Body lines, repeated to give each page a full text block. Density matters:
#: the margins are recognised by how far they sit from the text, which needs
#: the text to look like a text block.
TURN_BODY = [
    "The morning was cold and she walked the length of the",
    "garden without once looking back toward the quiet house",
    "where the others were still sleeping under heavy blankets.",
    "She had rehearsed the words for weeks and still they came",
    "out wrong whenever she tried to say them to anyone at all.",
    "There was frost on the grass and the light was very thin.",
    "Somewhere behind her a door opened and then closed again.",
    "She counted her steps to the gate and back, twice over.",
]

#: Pages whose last line stops mid-word, and the pages that finish it.
TURN_TAILS = {
    0: "and so at last she stopped and consid-",
    3: "the light on the water and the after-",
}
TURN_HEADS = {
    1: "ered what she might yet say to him before the day ended.",
    4: "noon folded itself away without any of them noticing it.",
}

#: Running heads that name the chapter, so no one of them appears on enough
#: pages to be found by counting repeated text. Position has to catch these.
TURN_CHAPTERS = [
    "ONE: The Garden", "ONE: The Garden", "TWO: The Letters",
    "TWO: The Letters", "THREE: The Water", "THREE: The Water",
]

TURN_FIRST_FOLIO = 40


def build_page_turn(path: str | Path) -> Path:
    """A proof where words divide across page boundaries."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path), pagesize=A5)
    width, height = A5

    for index in range(len(TURN_CHAPTERS)):
        pdf.setFont("Times-Roman", 8)
        pdf.drawCentredString(width / 2, height - 40, TURN_CHAPTERS[index])

        body = (
            ([TURN_HEADS[index]] if index in TURN_HEADS else [])
            + TURN_BODY
            + ([TURN_TAILS[index]] if index in TURN_TAILS else [])
        )
        y = height - 75
        for line in body:
            x = 45
            for word in line.split(" "):
                pdf.setFont("Times-Roman", 10)
                pdf.drawString(x, y, word)
                x += pdf.stringWidth(word + " ", "Times-Roman", 10)
            y -= 16

        pdf.setFont("Times-Roman", 9)
        pdf.drawCentredString(width / 2, 32, str(TURN_FIRST_FOLIO + index))
        pdf.showPage()

    pdf.save()
    return path


if __name__ == "__main__":
    fixtures = Path(__file__).parent / "fixtures"
    print(build(fixtures / "sample_proof.pdf"))
    print(build_page_turn(fixtures / "page_turn_proof.pdf"))
