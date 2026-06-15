# LuckNooz — working core

NewZoid-style headline remixer. Determinative method: fixed all-forms verb set
decides splits; LemmInflect handles re-inflection only.

## Files
- `lucknooz.py`      — the core: parse stage + assembly stage. Run directly for a demo.
- `verbset_full.json`— comprehensive all-forms verb set (27,302 forms from 6,748
                       lemmas), extracted from LemmInflect's own inflection table.
- `seed_verbs.json`  — the live verb set the module loads (currently a copy of the full set).
- `corpus.py`        — 50 labeled test headlines for measuring yield / bad splits.

## Run
    pip install lemminflect --break-system-packages
    python3 lucknooz.py

## Design decisions (settled)
1. Verb detection = FIXED ALL-FORMS SET only. No POS tagger. A word is a verb iff
   its normalized form is in the set. Transparent and determinate.
2. Split rule: first word in the set is the cut. If it's word #1 (no subject), take
   the SECOND verb; if there's no second, DISCARD the headline.
3. Traveling unit: the verb + everything after it move together as the predicate.
4. Pairing: subject from one headline, predicate from another, chosen at RANDOM.
5. Re-inflection: LemmInflect lemmatizes the moved verb and re-inflects it to agree
   with the NEW subject's number. The set does detection ONLY; LemmInflect does form.
6. Seed the set from a comprehensive verb list (done — from LemmInflect), so coverage
   is not the bottleneck. Curate DOWNWARD (remove troublemakers) rather than upward.
7. NO discard-on-stray-second-verb rule. We tried it ("option 2") and measured that
   under a comprehensive set it fires on ordinary object-nouns that happen to be verb
   forms (test, record, plan, homes, crops...), killing ~half of good headlines.
   Decision: drop it. Let the set run loose. Occasional "report shows" double-verb
   wrecks are accepted as part of the surreal effect; in practice they're rare because
   the bad predicate only bites when it gets reattached.

## PROPOSAL: bad-pairs list for double-verb wrecks (UNDER CONSIDERATION)
Daniel's idea: build, gradually over time, a list of word PAIRS where the first
"verb" is really a noun ("courts convicts", "delays disrupts", "market soar",
"strikes kill"). The program checks the list and discards those fragments.

Why this beats blunt downward-curation: it's targeted. The bad pair lives inside
the PREDICATE fragment at parse time (born malformed), before any recombination.
So the check belongs in find_split, on the fragment's first two words — NOT on the
final remixed headline.

Relationship to the old "option 2": option 2 discarded ANY fragment whose first two
words were both verb-set members, which over-fired (killed "develop test",
"unveils plan"). This proposal keeps the adjacency signal but only discards when the
specific pair is on a HUMAN-CURATED list. Precision without the collateral.
"courts convicts" -> listed -> discard. "develop test" -> never listed -> survives.

Mechanism:
  - bad_pairs.txt: confirmed pairs, one per line, starts ~empty, grows only when a
    real wreck is witnessed and judged wreck-shaped (not funny).
  - In find_split: after producing a fragment, if predicate's first two words
    (lowercased) match a listed pair -> discard. Else keep.

Decision to make: what is a "pair"?
  (1) literal surface pair ("courts convicts") — most precise; list grows across
      inflections. RECOMMENDED START: matches Daniel's mental model exactly.
  (2) lemma pair ("court convict") — one entry covers all inflections; smaller list;
      leans on LemmInflect at check time; can over-match.
  (3) first-word-only — collapses back toward blunt curation; rejected.

Build-alongside aids (make gradual list-growing low-effort):
  - candidate-flagging: generator emits a side list of every fragment whose first two
    words are both verb-set members = the review/suspect queue. Skim, copy real
    wrecks into bad_pairs.txt. Don't hunt through finished editions.
  - log discards so the list is seen working / catch over-matching.

Open sub-question: include the suspect-queue tooling now, or just the bad_pairs.txt
check first and add the review aid later?

## Open question from the live-headline run (DEFERRED — decide later)
Running real June 2026 headlines surfaced the COMPOUND-SUBJECT problem, not seen
in the hand-built corpus: headlines lead with modifiers ("Massive blaze engulfs",
"Federal judge rules", "Russian strikes kill", "Spain's king offers"). The verb set
contains the head noun as a verb form (blaze, judge, strike, king), so the split
fires too early — severing the modifier from its noun and stranding a fragment
("Massive" alone as subject). Same root cause as the "report shows" trap (noun that
is also a verb form), but more frequent in real headlines because they front-load
modifiers. Comprehensive set makes it worse (more verb-forms = more premature cuts).

Two paths, undecided:
  (a) Surgical: curate the high-collision words out of the set (king, judge, strike,
      blaze, cases, talks...). Stays determinative, no tagger. Targets the symptom.
  (b) Structural: let something identify the head noun for SUBJECT detection only.
      More reliable but reopens the determinism question that was deliberately settled.
Lean (a) first; only consider (b) if curation stops paying off.

## Server-side architecture (BUILT)
- `generate.py` — fetches real RSS headlines, parses + remixes via the core, writes
  `lucknooz.json` (with generated_at timestamp + source counts). Falls back to
  corpus.py if no feed is reachable, so a build is never empty.
- `index.html` — static page; reads lucknooz.json and renders the edition. No NLP in
  the browser. Styled in the Luckism family (burnt sienna, Fraunces + Spectral).
- `.github/workflows/refresh.yml` — runs generate.py every 6 hours, commits the JSON.

### Deploy
1. Push generate.py, lucknooz.py, corpus.py, index.html, requirements (lemminflect),
   and .github/workflows/refresh.yml to a GitHub repo.
2. Enable GitHub Pages (serve from the repo root or /docs).
3. The scheduled Action regenerates lucknooz.json; Pages serves the static page.
   (RSS feeds reach fine from GitHub Actions; only the dev sandbox blocks them.)

## Not yet built (deliberately deferred)
- PP-swap second pass: detach trailing prepositional phrases and exchange them across
  recombined headlines. Comes AFTER the verb split, as an optional toggleable stage.
- Plural-subject heuristic could be sharpened (collective nouns like "Police",
  "Government" read singular to the heuristic but plural to a human).
- Downward curation of high-collision noun/verb forms (see open question above).
