#!/usr/bin/env python3
"""
spell_check.py: every word on a resume its dictionary doesn't know, and every
doubled word, so the page goes out with zero errors (references/writing.md,
Spelling).

Two spelling errors cut a resume's interview odds by 7.3 points, and five by
18.5, in a test with 445 recruiters [S112]. A dictionary passes a real word in
the wrong place, so the check also flags, for a second read, a short list of
real words often typed for others: "manger", "form" for "from", "then" for
"than", "Lead" opening a bullet in a role that has ended. That list is the
skill's judgment.

It skips names (a capitalized word inside a sentence, or one that appears that
way anywhere on the page), acronyms, words with a capital inside them
(BizzyPlanit), words with digits, web and email addresses, the company and city
on each role line, and every word in --words FILE: the rulings file's "Words
the spell check passes" section, or a plain list.

The dictionary is outside the script. It uses the first one it finds: the
hunspell program, the aspell program, a hunspell dictionary file (en_US.dic,
which LibreOffice installs), the Python package pyspellchecker, or
/usr/share/dict/words. With none, it says the check did not run, which is not
a pass.

Reads a .docx, the JSON source, or a .txt or .md resume, the same way
draft_review.py does. Stdlib only.

Usage:
    python spell_check.py resume.docx
    python spell_check.py resume.docx --words rulings.md
    python spell_check.py resume.json --dict /path/to/en_US.dic

Exit codes: 0 clean (second reads may remain), 1 unknown or doubled words,
3 no dictionary found, so the check did not run.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import draft_review as dr  # noqa: E402

DIC_PLACES = (
    "/usr/share/hunspell/en_US.dic",
    "/usr/share/myspell/en_US.dic",
    "/usr/share/myspell/dicts/en_US.dic",
    "/usr/lib/libreoffice/share/extensions/dict-en/en_US.dic",
    "/opt/libreoffice/share/extensions/dict-en/en_US.dic",
    "/Applications/LibreOffice.app/Contents/Resources/extensions/dict-en/en_US.dic",
    "C:/Program Files/LibreOffice/share/extensions/dict-en/en_US.dic",
)
WORDS_FILE = "/usr/share/dict/words"

# Real words a dictionary passes, often typed for another word. Each is a
# second read, never a fail.
CONFUSABLES = [
    (re.compile(r"\bmanger\b", re.I), "manager?"),
    (re.compile(r"\bpubic\b", re.I), "public?"),
    (re.compile(r"\bform\s+(?:\$?\d|(?:19|20)\d{2}\b)", re.I), "from?"),
    (re.compile(r"\b(?:moved|came|grew|rose|fell|dropped|up|down|away|apart)\s+form\b", re.I), "from?"),
    (re.compile(r"\b(?:more|less|fewer|better|worse|greater|higher|lower|larger|smaller|faster|"
                r"slower|rather|other)\s+then\b", re.I), "than?"),
    (re.compile(r"\b(?:an|the|positive|negative|direct)\s+affect\b", re.I), "effect?"),
    (re.compile(r"\bprinciple\s+(?:designer|engineer|consultant|strategist|investigator|architect|"
                r"planner|scientist|analyst|partner)\b", re.I), "principal?"),
    (re.compile(r"\b(?:to|will|can|could|would)\s+loose\b", re.I), "lose?"),
]

URLS = re.compile(r"\S+@\S+|https?://\S+|www\.\S+|\b[\w-]+\.(?:com|org|net|io|co|edu|gov|ai|app)\b\S*",
                  re.I)
_LETTERS = "A-Za-z\u00c0-\u024f"
TOKEN = re.compile(rf"[{_LETTERS}][{_LETTERS}'\u2019]*(?:[-\u2011][{_LETTERS}][{_LETTERS}'\u2019]*)*")
DOUBLED = re.compile(r"\b([A-Za-z]+)\s+\1\b", re.I)
# The front of a hyphenated word that isn't a word alone: "pre-revenue", "co-led".
PREFIXES = set("""pre post co non re sub multi inter intra anti semi mid self cross ex pro mis bi
tri over under out up de un in e""".split())


# ------------------------------------------------------------ dictionaries --

class HunspellFile:
    """A hunspell .dic and .aff pair, read directly: the words, and the prefix
    and suffix rules that make "managers" and "rebuilt" from "manager" and
    "build"."""

    name = "hunspell dictionary file"

    def __init__(self, dic):
        self.where = dic
        aff = str(Path(dic).with_suffix(".aff"))
        self.words = {}
        lines = Path(dic).read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            word, _, flags = line.partition("/")
            word = word.split()[0] if word.split() else ""
            flags = flags.split()[0] if flags.split() else ""
            if word:
                self.words.setdefault(word, set()).update(flags)
        self.sfx, self.pfx, self.only_in_compound = [], [], set()
        rules = Path(aff).read_text(encoding="utf-8", errors="ignore").splitlines()
        i = 0
        while i < len(rules):
            parts = rules[i].split()
            if len(parts) >= 2 and parts[0] == "ONLYINCOMPOUND":
                self.only_in_compound.add(parts[1])
            if (len(parts) >= 4 and parts[0] in ("SFX", "PFX") and parts[2] in ("Y", "N")
                    and parts[3].isdigit()):
                kind, flag, cross, count = parts[0], parts[1], parts[2] == "Y", int(parts[3])
                for line in rules[i + 1:i + 1 + count]:
                    r = line.split()
                    if len(r) < 4:
                        continue
                    strip = "" if r[2] == "0" else r[2]
                    add = r[3].split("/")[0]
                    add = "" if add == "0" else add
                    cond = r[4] if len(r) > 4 else "."
                    try:
                        rx = re.compile(cond + "$" if kind == "SFX" else "^" + cond)
                    except re.error:
                        continue
                    (self.sfx if kind == "SFX" else self.pfx).append((flag, strip, add, rx, cross))
                i += count + 1
                continue
            i += 1

    def _has(self, word, flag=None):
        flags = self.words.get(word)
        if flags is None or flags & self.only_in_compound:
            return False
        return flag is None or flag in flags

    def _known(self, w):
        if self._has(w):
            return True
        for flag, strip, add, rx, _cross in self.sfx:
            if add and w.endswith(add) and len(w) > len(add):
                stem = w[:len(w) - len(add)] + strip
                if rx.search(stem) and self._has(stem, flag):
                    return True
        for flag, strip, add, rx, cross in self.pfx:
            if add and w.startswith(add) and len(w) > len(add):
                stem = strip + w[len(add):]
                if rx.search(stem) and self._has(stem, flag):
                    return True
                if not cross:
                    continue
                for f2, s2, a2, rx2, c2 in self.sfx:
                    if c2 and a2 and stem.endswith(a2) and len(stem) > len(a2):
                        base = stem[:len(stem) - len(a2)] + s2
                        if rx2.search(base) and self._has(base, f2) and self._has(base, flag):
                            return True
        return False

    def unknown(self, words):
        out = set()
        for w in words:
            forms = {w, w.lower(), w[:1].upper() + w[1:].lower()}
            if not any(self._known(f) for f in forms):
                out.add(w)
        return out


class Program:
    """The hunspell or aspell program, given one word per line."""

    def __init__(self, name, cmd):
        self.name, self.cmd, self.where = name, cmd, shutil.which(cmd[0])

    def unknown(self, words):
        words = sorted(words)
        if not words:
            return set()
        proc = subprocess.run(self.cmd, input="\n".join(words), capture_output=True, text=True)
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip() or f"{self.cmd[0]} stopped")
        return {w for w in proc.stdout.split() if w}


class PySpell:
    name = "pyspellchecker"

    def __init__(self):
        from spellchecker import SpellChecker   # not stdlib: used only when installed
        self.sc, self.where = SpellChecker(), "Python package"

    def unknown(self, words):
        lower = {w.lower(): w for w in words}
        return {lower[w] for w in self.sc.unknown(list(lower))}


class WordList:
    name = "word list"

    def __init__(self, path):
        self.where = path
        self.words = {w.strip().lower() for w in
                      Path(path).read_text(encoding="utf-8", errors="ignore").splitlines() if w.strip()}

    def unknown(self, words):
        return {w for w in words if w.lower() not in self.words}


def find_dictionary(dic=None):
    """The first dictionary that works, or None."""
    if dic:
        return HunspellFile(dic)
    for name, cmd in (("hunspell program", ["hunspell", "-l", "-d", "en_US"]),
                      ("aspell program", ["aspell", "list", "--lang=en"])):
        if shutil.which(cmd[0]):
            prog = Program(name, cmd)
            try:
                prog.unknown({"test"})
                return prog
            except (RuntimeError, OSError):
                pass
    env = os.environ.get("SPELL_CHECK_DIC")
    for place in ([env] if env else []) + list(DIC_PLACES):
        if place and Path(place).is_file() and Path(place).with_suffix(".aff").is_file():
            return HunspellFile(place)
    try:
        return PySpell()
    except ImportError:
        pass
    if Path(WORDS_FILE).is_file():
        return WordList(WORDS_FILE)
    return None


# ------------------------------------------------------------------ words --

def load_word_list(path):
    """The words in a rulings file's "Words the spell check passes" section, or
    in a plain list (one per line or comma-separated)."""
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"^##\s+Words the spell check passes\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if m:
        body = m.group(1)
    elif re.search(r"^##\s", text, re.M):
        return set()                 # a rulings file without the section
    else:
        body = text
    words = set()
    for line in body.splitlines():
        line = line.strip().lstrip("-*").strip()
        if not line or line.startswith(("#", "(", ">")) or line.lower().startswith(("names,", "names ")):
            continue
        line = re.sub(r"^example:\s*", "", line, flags=re.I)
        for w in re.split(r"[,\s]+", line):
            w = w.strip(".;:\"'()")
            if w:
                words.add(w.lower())
    return words


def lines_to_check(blocks):
    """(block number, text, kind) for every line worth reading. A role line
    gives its title only: the company and the city are names."""
    out, first = [], True
    for b in dr.structure(blocks):
        if first and b.kind == "para":
            first = False           # the candidate's name
            continue
        if b.kind == "para" and dr.CONTACT.search(b.text):
            continue                # the contact line: city, phone, email, links
        if b.kind == "role":
            title = (b.role or {}).get("title", "")
            if title:
                out.append((b.n, title, "title"))
            continue
        if b.text.strip():
            out.append((b.n, b.text, b.kind))
    return out


def words_in(text):
    """(word, starts a sentence) for each word, with URLs, emails and words
    touching a digit left out. Hyphenated words come apart."""
    t = URLS.sub(" ", dr.plain(text))
    out = []
    for m in TOKEN.finditer(t):
        before, after = t[m.start() - 1:m.start()], t[m.end():m.end() + 1]
        if before.isdigit() or after.isdigit():
            continue
        word = re.sub(r"'s$|'$", "", m.group(0))
        initial = dr.sentence_initial(t, m.start())
        parts = re.split(r"[-\u2011]", word)
        for i, part in enumerate(parts):
            if part and not (len(parts) > 1 and i < len(parts) - 1 and part.lower() in PREFIXES):
                out.append((part, initial))
            initial = False
    return out


def is_name_like(word):
    return word.isupper() or bool(re.search(r"[a-z][A-Z]", word))


def check(blocks, dictionary, allowed=frozenset()):
    """(unknown, doubled, second reads), each a list of (block number, text)."""
    lines = lines_to_check(blocks)
    caps_inside = set()
    for _n, text, kind in lines:
        if kind == "title":
            continue
        for w, initial in words_in(text):
            if w[:1].isupper() and not initial:
                caps_inside.add(w)

    candidates = {}
    for n, text, kind in lines:
        title_case = kind == "title" or (n <= 3 and kind == "para")
        for w, initial in words_in(text):
            if len(w) < 2 or is_name_like(w) or w.lower() in allowed:
                continue
            if w[:1].isupper() and not title_case:
                if not initial or w in caps_inside:
                    continue          # a name
            candidates.setdefault(w, n)
    unknown = dictionary.unknown(set(candidates))
    bad = sorted(((candidates[w], w) for w in unknown), key=lambda x: (x[0], x[1].lower()))

    doubled, second = [], []
    for n, text, kind in lines:
        for m in DOUBLED.finditer(dr.plain(text)):
            doubled.append((n, m.group(0)))
        for rx, hint in CONFUSABLES:
            for m in rx.finditer(dr.plain(text)):
                second.append((n, f"{m.group(0)} ({hint})"))
    marked = dr.structure(blocks)
    for b in marked:
        if (b.kind == "bullet" and dr.is_experience(b.section) and b.role
                and not re.match(r"(?i)present|current|now", b.role.get("end", "") or "present")
                and re.match(r"\s*Lead\b", dr.plain(b.text))):
            second.append((b.n, "Lead (Led? The role has ended)"))
    return bad, doubled, second


# ------------------------------------------------------------------- main --

def parse_args(argv):
    files, opts, i = [], {"words": None, "dict": None}, 0
    while i < len(argv):
        a = argv[i]
        key = a.split("=", 1)[0]
        if key in ("--words", "--dict"):
            _k, eq, value = a.partition("=")
            if not eq:
                i += 1
                if i >= len(argv):
                    sys.exit(f"{key} needs a file.")
                value = argv[i]
            opts[key[2:]] = value
        elif a.startswith("-"):
            sys.exit(f"Unknown option {a}.\n{__doc__}")
        else:
            files.append(a)
        i += 1
    return files, opts


def main():
    files, opts = parse_args(sys.argv[1:])
    if len(files) != 1:
        sys.exit(__doc__)
    blocks = dr.load(files[0])
    if not blocks:
        sys.exit("Nothing to read.")
    allowed = load_word_list(opts["words"]) if opts["words"] else set()
    dictionary = find_dictionary(opts["dict"])
    print("=" * 70)
    print("SPELL CHECK")
    print("=" * 70)
    if dictionary is None:
        print("No dictionary found: no hunspell or aspell program, no en_US.dic, no")
        print("pyspellchecker, no /usr/share/dict/words. The check did not run, and that")
        print("is not a pass. Install one (LibreOffice brings en_US.dic), or pass --dict.")
        print("=" * 70)
        return 3
    print(f"Dictionary: {dictionary.name} ({dictionary.where})")
    if opts["words"]:
        print(f"Word list: {len(allowed)} words from {opts['words']}")
    bad, doubled, second = check(blocks, dictionary, allowed)

    if bad:
        print("\nFAIL: words the dictionary doesn't know. Fix each one, or add it to the")
        print("word list in the rulings file if it's spelled right.")
        print("-" * 70)
        for n, w in bad:
            print(f"  block {n}: \"{w}\"")
    if doubled:
        print("\nFAIL: a word twice in a row.")
        print("-" * 70)
        for n, w in doubled:
            print(f"  block {n}: \"{w}\"")
    if not bad and not doubled:
        print("\nFAIL: none.")
    if second:
        print("\nREVIEW: real words often typed for others. Read these again.")
        print("-" * 70)
        for n, w in second:
            print(f"  block {n}: {w}")
    fails = len(bad) + len(doubled)
    print("\n" + "=" * 70)
    print(f"{fails} to fix, {len(second)} to read again. A clean run can still miss a real")
    print("word in the wrong place, so read the page once more.")
    print("=" * 70)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
