#!/usr/bin/env python3
"""lint_games.py [banks dir] -- check games/scramble.json and games/riddles.json for the GRV TV game rounds.
Hard errors (exit 1): schema, lengths, duplicate ids/answers, scramble not a true permutation, scramble equal to the word,
scramble that is itself a dictionary word, banned topics. Warnings: a word with another dictionary anagram (players could
'solve' it differently), near-duplicate riddles."""
import json, os, re, sys, collections
D = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
DICT = set(w.strip().upper() for w in open('/usr/share/dict/words') if w.strip().isalpha())
BANNED = r'\b(beer|wine|vodka|whiske?y|rum|gin|liquor|booze|keg|pub|tavern|drunk|cocktail|brew(ery)?|hangover|champagne|bourbon|tequila|margarita|martini|' \
         r'drug|drugs|pill|pills|weed|marijuana|cannabis|opioid|heroin|cocaine|meth|needle|syringe|overdose|dose|smok(e|ing)|cigar(ette)?|tobacco|vape|nicotine|' \
         r'casino|gambl\w*|poker|lottery|jackpot|bet|betting|wager|slot machine|' \
         r'gun|guns|rifle|pistol|shoot\w*|kill\w*|murder\w*|dead|death|die|dies|died|dying|blood\w*|bomb\w*|war|weapon\w*|knife|knives|grave|coffin|funeral|ghost|skull|' \
         r'hospital|surgery|disease|cancer|suicide|prison|jail|crime|steal\w*|thief|robber\w*)\b'
SENSITIVE = ['NEGR', 'NIGG', 'NIGA', 'FAG', 'KIKE', 'SPIC', 'CHINK', 'COON', 'DYKE', 'PERC', 'METH', 'COKE', 'CRACK', 'DOPE', 'WEED', 'HIGH', 'PILL', 'OXY', 'HERO', 'BOOZE', 'BEER', 'WINE', 'RUM', 'GIN', 'SHOT', 'SEX', 'ASS', 'TIT', 'CUM', 'FUC', 'FUK', 'SHIT', 'PISS', 'DICK', 'DIK', 'COCK', 'PORN', 'DAMN', 'KILL', 'DEAD', 'GUN', 'RAPE', 'NAZI', 'HOE', 'SLUT', 'WHORE', 'BUTT', 'POOP', 'CRAP', 'PUKE', 'DIE']
err, warn = [], []
def chk(cond, msg, hard=True): (None if cond else (err if hard else warn).append(msg))
# ---- scramble
p = os.path.join(D, 'scramble.json')
if os.path.exists(p):
    b = json.load(open(p)); items = b.get('items', []); chk(isinstance(items, list) and len(items) >= 40, 'scramble: need >= 40 items')
    ids, words = set(), set()
    for it in items:
        i = it.get('id', '?'); w = str(it.get('word', '')).upper(); s = str(it.get('scramble', '')).upper()
        chk(set(it) <= {'id', 'cat', 'word', 'scramble', 'clue', 'fact'} and all(it.get(k) for k in ('id', 'cat', 'word', 'scramble', 'clue')), '%s: needs id, cat, word, scramble, clue (fact optional), no other keys' % i)
        chk(i not in ids, '%s: duplicate id' % i); ids.add(i)
        chk(w not in words, '%s: duplicate word %s' % (i, w)); words.add(w)
        chk(re.fullmatch(r'[A-Z]{4,9}', w or '') is not None, '%s: word must be 4-9 letters A-Z (got %r)' % (i, w))
        chk(sorted(w) == sorted(s), '%s: scramble %r is not a permutation of %r' % (i, s, w))
        chk(s != w, '%s: scramble equals the word' % i)
        chk(s not in DICT, '%s: scramble %r is itself a dictionary word' % (i, s))
        bad_sub = [x for x in SENSITIVE if x in s or x in s[::-1]]
        chk(not bad_sub, '%s: scramble %r contains %s' % (i, s, '/'.join(bad_sub)))
        chk(sum(a == c for a, c in zip(s, w)) <= len(w) // 3, '%s: scramble %r keeps too many letters in place' % (i, s))
        chk(len(it.get('clue', '')) <= 60, '%s: clue over 60 chars' % i); chk(len(it.get('fact', '') or '') <= 110, '%s: fact over 110 chars' % i)
        chk(len(it.get('cat', '')) <= 24, '%s: cat over 24 chars' % i)
        txt = ' '.join(str(it.get(k, '')) for k in ('word', 'clue', 'fact', 'cat'))
        chk(re.search(BANNED, txt, re.I) is None, '%s: banned topic: %s' % (i, re.search(BANNED, txt, re.I).group(0) if re.search(BANNED, txt, re.I) else ''))
        chk(w.lower() not in it.get('clue', '').lower(), '%s: clue gives the word away' % i)
        others = sorted(x for x in DICT if len(x) == len(w) and x != w and sorted(x) == sorted(w)) if len(w) <= 7 else []
        chk(not others, '%s: %s also unscrambles to %s' % (i, w, ', '.join(others[:4])), hard=False)
    print('scramble: %d items, %d categories' % (len(items), len(set(i.get('cat') for i in items))))
# ---- riddles
p = os.path.join(D, 'riddles.json')
if os.path.exists(p):
    b = json.load(open(p)); items = b.get('items', []); chk(isinstance(items, list) and len(items) >= 30, 'riddles: need >= 30 items')
    ids, qs = set(), collections.Counter()
    for it in items:
        i = it.get('id', '?')
        chk(set(it) <= {'id', 'kind', 'q', 'a', 'why'} and all(it.get(k) for k in ('id', 'kind', 'q', 'a')), '%s: needs id, kind, q, a (why optional), no other keys' % i)
        chk(it.get('kind') in ('riddle', 'teaser'), '%s: kind must be riddle or teaser' % i)
        chk(i not in ids, '%s: duplicate id' % i); ids.add(i)
        chk(len(it.get('q', '')) <= 150, '%s: q over 150 chars' % i); chk(len(it.get('a', '')) <= 40, '%s: answer over 40 chars' % i)
        chk(len(it.get('why', '') or '') <= 120, '%s: why over 120 chars' % i)
        txt = ' '.join(str(it.get(k, '')) for k in ('q', 'a', 'why'))
        m = re.search(BANNED, txt, re.I); chk(m is None, '%s: banned topic: %s' % (i, m.group(0) if m else ''))
        key = re.sub(r'[^a-z]', '', it.get('q', '').lower())[:40]; qs[key] += 1
    for k, n in qs.items(): chk(n == 1, 'riddles: near-duplicate question start %r x%d' % (k, n), hard=False)
    print('riddles: %d items (%d riddle, %d teaser)' % (len(items), sum(i.get('kind') == 'riddle' for i in items), sum(i.get('kind') == 'teaser' for i in items)))
for w in warn: print('WARN', w)
for e in err: print('ERROR', e)
print('OK' if not err else '%d errors' % len(err)); sys.exit(1 if err else 0)
