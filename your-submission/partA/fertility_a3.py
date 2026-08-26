#!/usr/bin/env python3
"""
fertility_a3.py -- Part A3: corrected cross-language analysis.

Applies the A2-identified fixes by default (no asymmetric
lowercasing, proper whitespace splitting via .split(), pooled
sum(tokens)/sum(denominator) instead of mean-of-ratios) and computes
FOUR denominators: whitespace words, UTF-8 bytes, grapheme clusters,
and parallel sentences -- across however many tokenizers/languages
you pass in.

Requires:
    pip install regex --break-system-packages   (for grapheme clusters)

Usage:
    python fertility_a3.py \
        --corpus eng=corpus/eng.txt --corpus hin=corpus/hin.txt \
        --corpus kan=corpus/kan.txt --corpus tam=corpus/tam.txt \
        --tokenizer gpt2 \
        --tokenizer hf:xlm-roberta-base
"""
import argparse
import unicodedata

import regex


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


def analyze(lines, encode):
    total_tokens = 0
    total_words = 0
    total_bytes = 0
    total_graphemes = 0
    n_sentences = len(lines)
    for line in lines:
        # deliberately NOT lowercasing -- A2 found asymmetric
        # lowercasing biases the cross-language comparison
        tokens = encode(line)
        words = line.split()  # A2 fix: proper whitespace split
        total_tokens += len(tokens)
        total_words += len(words)
        total_bytes += len(line.encode("utf-8"))
        total_graphemes += len(regex.findall(r"\X", line))
    return {
        "tok_per_word": total_tokens / total_words,
        "tok_per_byte": total_tokens / total_bytes,
        "tok_per_grapheme": total_tokens / total_graphemes,
        "tok_per_sentence": total_tokens / n_sentences,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", action="append", required=True, metavar="LANG=PATH")
    ap.add_argument("--tokenizer", action="append", required=True)
    args = ap.parse_args()

    corpora = {}
    for spec in args.corpus:
        lang, path = spec.split("=", 1)
        corpora[lang] = read_lines(path)

    for tok_spec in args.tokenizer:
        print(f"\n=== tokenizer: {tok_spec} ===")
        encode = load_tokenizer(tok_spec)
        results = {lang: analyze(lines, encode) for lang, lines in corpora.items()}

        header = f"{'lang':<6}{'tok/word':>10}{'tok/byte':>10}{'tok/grph':>10}{'tok/sent':>10}"
        print(header)
        print("-" * len(header))
        for lang, r in results.items():
            print(f"{lang:<6}{r['tok_per_word']:>10.3f}{r['tok_per_byte']:>10.4f}"
                  f"{r['tok_per_grapheme']:>10.3f}{r['tok_per_sentence']:>10.2f}")

        base = list(results)[0]
        print(f"\nratios vs {base}:")
        for lang in list(results)[1:]:
            for metric in ["tok_per_word", "tok_per_byte", "tok_per_grapheme", "tok_per_sentence"]:
                ratio = results[lang][metric] / results[base][metric]
                print(f"  {lang}/{base}  {metric:<18}: {ratio:.3f}x")


if __name__ == "__main__":
    main()
