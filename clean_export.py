#!/usr/bin/env python3
"""Synthetic demonstration: normalize a CSV without guessing or losing rows."""
import argparse
import csv
import html
import json
import re
from pathlib import Path


def safe(value):
    value = str(value or '')
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value


def clean(source, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with Path(source).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        if not {'name', 'email', 'company', 'source'}.issubset(fields):
            raise ValueError('Required columns: name, email, company, source')
        rows = list(reader)
    accepted, review, duplicates = [], [], []
    seen = {}
    for line, raw in enumerate(rows, 2):
        row = {k: (raw.get(k) or '').strip() for k in fields}
        row['email'] = row['email'].lower()
        if None in raw:
            reason = 'More values than columns'
        elif any(raw.get(k) is None for k in fields):
            reason = 'Missing column values'
        elif not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', row['email']):
            reason = 'Email needs correction'
        elif not row['name']:
            reason = 'Name missing'
        elif row['email'] in seen:
            if seen[row['email']] == row:
                duplicates.append({'line': line, 'reason': 'Exact normalized duplicate', 'raw': raw})
                continue
            reason = 'Same email, different values; no automatic merge'
        else:
            seen[row['email']] = row
            accepted.append(row)
            continue
        review.append({'line': line, 'reason': reason, 'raw': raw})
    with (destination / 'clean.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: safe(v) for k, v in row.items()} for row in accepted)
    audit = {'syntheticDemo': True, 'inputRows': len(rows), 'accepted': len(accepted),
             'needsReview': len(review), 'duplicates': len(duplicates),
             'accountedRows': len(accepted) + len(review) + len(duplicates),
             'review': review, 'duplicateRows': duplicates, 'originalRows': rows}
    assert audit['inputRows'] == audit['accountedRows']
    (destination / 'audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    reasons = ''.join('<li>Row ' + str(x['line']) + ': ' + html.escape(x['reason']) + '</li>' for x in review)
    (destination / 'report.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Export repair demonstration</title>
<style>body{font:18px/1.6 system-ui;background:#f6f5ef;color:#183c32;max-width:850px;margin:60px auto;padding:24px}h1{font-size:42px;line-height:1.15}.stats{display:flex;flex-wrap:wrap;gap:16px}.stats p{background:white;padding:20px;border:1px solid #d6ded8;border-radius:12px}strong{font-size:30px;display:block}small{color:#52665d}</style>
<small>KRASYN WORKFLOW REPAIR · SYNTHETIC DEMONSTRATION</small><h1>A messy export.<br>A usable file and a clear audit.</h1>
<p>Whitespace and email casing normalized. Exact duplicates separated. Conflicting records held for review. Every input row preserved in the audit.</p><div class="stats">'''
        + ''.join('<p><strong>' + str(v) + '</strong>' + label + '</p>' for label, v in [('Input rows', len(rows)), ('Usable records', len(accepted)), ('Needs review', len(review)), ('Exact duplicates', len(duplicates))])
        + '</div><h2>Needs a decision</h2><ul>' + reasons + '</ul><p>Spreadsheet formula prefixes are escaped in the CSV. Original values remain in audit.json. Nothing is uploaded or sent.</p><small>This demonstrates delivery capability, not a customer result. Python 3 standard library only.</small></html>', encoding='utf-8')
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('destination')
    args = parser.parse_args()
    result = clean(args.source, args.destination)
    print(json.dumps({k: result[k] for k in ['inputRows', 'accepted', 'needsReview', 'duplicates', 'accountedRows']}))
