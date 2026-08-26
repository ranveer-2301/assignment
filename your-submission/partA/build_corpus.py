#!/usr/bin/env python3
"""
build_corpus.py -- Part A1: assemble a real multilingual eval corpus.
(v2 -- rewritten after Muennighoff/flores200's script-based loader
broke on datasets>=4.0, which dropped support for .py loading
scripts. This version downloads plain per-language text files
directly instead of going through load_dataset(), so it can't hit
that class of error again.)

Source: FLORES-200 devtest split, DGME/FLORES-200 mirror on
Hugging Face -- one file per language under devtest/, one sentence
per line, all languages line-aligned by construction (that's the
defining property of FLORES: same underlying sentence, translated
into every language, same line number = same content).

English source sentences are drawn equally from Wikinews,
Wikijunior, and Wikivoyage (per FLORES/FLORES+ documentation) --
cite this directly in your A1 caveats paragraph, no need to compute
it, this plain-file mirror doesn't carry a domain column.

Requires:
    pip install huggingface_hub --break-system-packages
    (already pulled in as a dependency when `datasets` installed)

Usage:
    python build_corpus.py --n 250 --seed 42 --outdir corpus
"""
import argparse
import os
import random

from huggingface_hub import hf_hub_download

REPO_ID = "DGME/FLORES-200"
LANGS = {
    "eng": "eng_Latn",
    "hin": "hin_Deva",
    "kan": "kan_Knda",
    "tam": "tam_Taml",
}


def fetch_lines(lang_code: str) -> list[str]:
    path = hf_hub_download(
        repo_id=REPO_ID,
        repo_type="dataset",
        filename=f"devtest/{lang_code}.devtest",
    )
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=250)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--outdir", default="corpus")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    per_lang_lines = {}
    n_lines = None
    for lang, code in LANGS.items():
        print(f"downloading {code} ...")
        lines = fetch_lines(code)
        per_lang_lines[lang] = lines
        if n_lines is None:
            n_lines = len(lines)
        elif len(lines) != n_lines:
            raise SystemExit(
                f"line count mismatch: {lang} has {len(lines)} lines, "
                f"expected {n_lines} -- files should be perfectly "
                f"line-aligned, something is off with this mirror"
            )
    print(f"loaded devtest split: {n_lines} parallel lines per language")

    random.seed(args.seed)
    idx = list(range(n_lines))
    random.shuffle(idx)
    idx = sorted(idx[: args.n])  # keep source order for readability

    for lang, lines in per_lang_lines.items():
        path = os.path.join(args.outdir, f"{lang}.txt")
        with open(path, "w", encoding="utf-8") as f:
            for i in idx:
                f.write(lines[i].strip() + "\n")
        print(f"wrote {args.n} lines -> {path}")


if __name__ == "__main__":
    main()
