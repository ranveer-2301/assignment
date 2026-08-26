#!/usr/bin/env python3
"""
fertility_variants.py -- Part A2: toggleable variants of fertility.py
to isolate and measure each suspected bug's effect, one flag at a time.

With no flags set, this reproduces fertility_original.py's behavior
exactly (same bugs, same output) -- that's your baseline. Toggle one
flag, rerun, diff against baseline -- that diff is your evidence.

Usage:
    # baseline -- matches the original script's (buggy) behavior
    python fertility_variants.py --corpus eng=corpus/eng.txt --corpus hin=corpus/hin.txt --tokenizer gpt2

    # isolate the split(" ") double-space bug
    python fertility_variants.py --corpus eng=corpus/eng.txt --corpus hin=corpus/hin.txt --tokenizer gpt2 --fix-split

    # isolate the asymmetric lowercasing (no-op for Hindi, real effect on English BPE)
    python fertility_variants.py --corpus eng=corpus/eng.txt --corpus hin=corpus/hin.txt --tokenizer gpt2 --no-lowercase

    # isolate mean-of-per-line-ratios vs pooled sum(tokens)/sum(words)
    python fertility_variants.py --corpus eng=corpus/eng.txt --corpus hin=corpus/hin.txt --tokenizer gpt2 --pooled

    # all three fixes together -- this is your "corrected" run to carry into A3
    python fertility_variants.py --corpus eng=corpus/eng.txt --corpus hin=corpus/hin.txt --tokenizer gpt2 --fix-split --no-lowercase --pooled
"""
import argparse
import unicodedata


def load_tokenizer(spec: str):
    if spec.startswith("hf:"):
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(spec[3:])
        return lambda s: tok.encode(s, add_special_tokens=False)
    else:
        import tiktoken
        enc = tiktoken.get_encoding(spec)
        return enc.encode


def read_lines(path):
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            line = unicodedata.normalize("NFC", line)
            lines.append(line)
    return lines


def analyze(lines, encode, fix_split, no_lowercase, pooled):
    per_line_fertility = []
    per_line_tpc = []
    total_tokens = 0
    total_words = 0
    for line in lines:
        if not no_lowercase:
            line = line.lower()
        tokens = encode(line)
        words = line.split() if fix_split else line.split(" ")
        chars = len(line)
        total_tokens += len(tokens)
        total_words += len(words)
        per_line_fertility.append(len(tokens) / len(words))
        per_line_tpc.append(len(tokens) / chars)
    n = len(per_line_fertility)
    fert = (total_tokens / total_words) if pooled else (sum(per_line_fertility) / n)
    tpc = sum(per_line_tpc) / n
    return fert, tpc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", action="append", required=True, metavar="LANG=PATH")
    ap.add_argument("--tokenizer", default="gpt2")
    ap.add_argument("--fix-split", action="store_true")
    ap.add_argument("--no-lowercase", action="store_true")
    ap.add_argument("--pooled", action="store_true")
    args = ap.parse_args()

    encode = load_tokenizer(args.tokenizer)

    print(f"tokenizer: {args.tokenizer}  |  fix_split={args.fix_split}  no_lowercase={args.no_lowercase}  pooled={args.pooled}")
    print(f"{'lang':<8}{'fertility (tok/word)':>22}{'tok/char':>12}")
    print("-" * 42)
    results = {}
    for spec in args.corpus:
        lang, path = spec.split("=", 1)
        lines = read_lines(path)
        fert, tpc = analyze(lines, encode, args.fix_split, args.no_lowercase, args.pooled)
        results[lang] = (fert, tpc)
        print(f"{lang:<8}{fert:>22.4f}{tpc:>12.4f}")

    if len(results) >= 2:
        langs = list(results)
        base = langs[0]
        print()
        for lang in langs[1:]:
            ratio = results[lang][0] / results[base][0]
            print(f"{lang} is {ratio:.3f}x the fertility of {base}")


if __name__ == "__main__":
    main()
