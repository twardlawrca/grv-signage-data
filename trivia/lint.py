#!/usr/bin/env python3
"""Lint trivia/bank.json before pushing: shape, lengths, duplicates and the fleet screening list (screen.json).
Run:  python3 trivia/lint.py            (from the repo root; exit 1 on any problem)"""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bank = json.load(open(os.path.join(ROOT, 'trivia', 'bank.json'), encoding='utf-8'))
terms = json.load(open(os.path.join(ROOT, 'screen.json'), encoding='utf-8')).get('exclude', [])
parts = []
for t in terms:
    t = str(t or '').strip().lower(); pre, suf = t.startswith('*'), t.endswith('*'); t = t.strip('*')
    if t: parts.append(('' if pre else r'\b') + r'\s+'.join(re.escape(w) for w in t.split()) + ('' if suf else r'\b'))
SCREEN = re.compile('(?:' + '|'.join(parts) + ')', re.I)
EXTRA = re.compile(r"\b(cocktail|liquor|rum|champagne|bourbon|cigar|cigarette|tobacco|vape|marijuana|cannabis|poker|blackjack|betting)\w*", re.I)
problems, seen, ids = [], set(), set()
items = bank.get('items') or []
for n, it in enumerate(items):
    where = '%s (%s)' % (it.get('id', '#%d' % n), str(it.get('q', ''))[:50])
    q, opts, fact = str(it.get('q', '')), it.get('options') or [], str(it.get('fact', ''))
    if not q.strip(): problems.append('%s: empty question' % where)
    if it.get('id') in ids: problems.append('%s: duplicate id' % where)
    ids.add(it.get('id'))
    key = re.sub(r'\W+', ' ', q.lower()).strip()
    if key in seen: problems.append('%s: duplicate question' % where)
    seen.add(key)
    if len(opts) != 4 or len(set(str(o).strip().lower() for o in opts)) != 4: problems.append('%s: needs 4 distinct options' % where)
    a = it.get('answer')
    if not isinstance(a, int) or not (0 <= a < len(opts)): problems.append('%s: answer must be an index into options' % where)
    if len(q) > 118: problems.append('%s: question longer than 118 characters (%d)' % (where, len(q)))
    for o in opts:
        if len(str(o)) > 40: problems.append('%s: option longer than 40 characters: %s' % (where, o))
    if len(fact) > 130: problems.append('%s: fact longer than 130 characters' % where)
    if not it.get('cat'): problems.append('%s: no category' % where)
    blob = ' '.join([q, fact] + [str(o) for o in opts])
    m = SCREEN.search(blob) or EXTRA.search(blob)
    if m: problems.append('%s: screened term "%s"' % (where, m.group(0)))
if len(items) < 50: problems.append('bank has only %d questions (a round needs a real pool)' % len(items))
if bank.get('count') != len(items): problems.append('count field (%s) is not the number of items (%d)' % (bank.get('count'), len(items)))
for p in problems: print('PROBLEM:', p)
print('%s: %d questions, %d categories, %d problems' % ('FAIL' if problems else 'OK', len(items), len(set(i.get('cat') for i in items)), len(problems)))
sys.exit(1 if problems else 0)
