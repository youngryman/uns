"""
LuckNooz — NewZoid-style headline remixer.

Determinative method, per Daniel's spec:
  - Verb detection is by FIXED ALL-FORMS SET only. No POS tagger.
  - Split rule: first word in the verb set is the cut point.
      * If that word is the FIRST word of the headline (no subject), take the SECOND verb instead.
      * If there is no second verb, DISCARD the headline.
  - Traveling unit: the verb and EVERYTHING after it move together as the predicate.
  - Pairing: subject from one headline, predicate from another, chosen at RANDOM.
  - Re-inflection: LemmInflect lemmatizes the moved verb, then re-inflects it
      to agree with the new subject's number. The verb SET does detection only;
      LemmInflect does the form change.
  - PP-swap: a separate, optional second pass (not in the core; added later).
"""

import json
import random
import re
from lemminflect import getInflection, getLemma


# ---------------------------------------------------------------------------
# The verb set — the single authoritative thing you curate.
# Seeded from V13's commonVerbs. All-forms: each surface form listed explicitly.
# ---------------------------------------------------------------------------
VERB_SET = set(json.load(open("verbset_full.json")))


# ---------------------------------------------------------------------------
# Bad pairs — human-curated list of "first-verb-is-really-a-noun" collisions.
# Each line is a surface pair, e.g.  report shows
# When the chosen split-verb + the next word match a listed pair, the chosen
# word was a NOUN: skip it and advance to the next verb (Daniel's recovery rule).
# The file is optional and starts ~empty; it grows as real wrecks are witnessed.
# ---------------------------------------------------------------------------
def load_bad_pairs(path="bad_pairs.txt"):
    pairs = set()
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.split("#", 1)[0].strip()  # allow # comments
                if not line:
                    continue
                toks = line.split()
                if len(toks) >= 2:
                    pairs.add((normalize(toks[0]), normalize(toks[1])))
    except FileNotFoundError:
        pass
    return pairs


def normalize(word):
    """Lowercase and strip non-letters for set membership testing."""
    return re.sub(r"[^a-z]", "", word.lower())


BAD_PAIRS = load_bad_pairs()


# ---------------------------------------------------------------------------
# Prepositions — a CLOSED class (finite, stable), so no ongoing curation needed.
# Used to (a) detect a salvageable trailing prepositional phrase, and
# (b) drive the PP-swap assembly stage.
# ---------------------------------------------------------------------------
PREPOSITIONS = {
    "about", "above", "across", "after", "against", "along", "amid", "among",
    "amongst", "around", "as", "at", "before", "behind", "below", "beneath",
    "beside", "besides", "between", "beyond", "by", "despite", "down", "during",
    "except", "for", "from", "in", "inside", "into", "near", "of", "off", "on",
    "onto", "outside", "over", "past", "since", "through", "throughout", "to",
    "toward", "towards", "under", "underneath", "until", "unto", "up", "upon",
    "via", "with", "within", "without",
}
# multiword prepositions, matched as leading bigrams of a tail
PREPOSITIONS_MULTI = {
    ("ahead", "of"), ("because", "of"), ("close", "to"), ("due", "to"),
    ("instead", "of"), ("next", "to"), ("out", "of"), ("prior", "to"),
    ("thanks", "to"), ("up", "to"), ("as", "for"), ("apart", "from"),
    ("regardless", "of"), ("according", "to"),
}


def extract_trailing_pp(text):
    """
    Find the LAST trailing prepositional phrase in `text`: the final run that
    begins with a preposition (simple or multiword) and continues to the end.
    Returns the PP string, or None if there's no trailing preposition.
    e.g. "disrupts production at outdoor event" -> "at outdoor event"
    """
    words = text.split()
    nwords = [normalize(w) for w in words]
    # scan from the end for the latest preposition that opens a tail
    for i in range(len(words) - 1, -1, -1):
        # multiword preposition starting at i?
        if i + 1 < len(words) and (nwords[i], nwords[i + 1]) in PREPOSITIONS_MULTI:
            if i + 2 <= len(words) - 1:  # something must follow the preposition
                return " ".join(words[i:])
        if nwords[i] in PREPOSITIONS and i <= len(words) - 2:
            return " ".join(words[i:])
    return None


def predicate_has_interior_bad_pair(predicate):
    """
    Scan ALL adjacent word-pairs inside a predicate against BAD_PAIRS.
    Returns the (i, pair) of the first match, or None. Used to detect a
    double-verb stumble that rides inside a traveling predicate.
    """
    words = predicate.split()
    nwords = [normalize(w) for w in words]
    for i in range(len(words) - 1):
        if (nwords[i], nwords[i + 1]) in BAD_PAIRS:
            return i, (nwords[i], nwords[i + 1])
    return None


def clean_predicate(parsed_fragment):
    """
    Predicate-interior cure (Daniel's rule):
      - If the predicate carries an interior bad pair, the fragment is poisoned.
      - Try to SALVAGE a trailing prepositional phrase from it -> return a
        {'salvaged_pp': '...'} marker for the PP pool.
      - If no trailing PP exists, signal DISCARD (return None).
      - If the predicate is clean, return it unchanged.
    """
    pred = parsed_fragment["predicate"]
    if predicate_has_interior_bad_pair(pred) is None:
        return parsed_fragment  # clean, keep as-is
    pp = extract_trailing_pp(pred)
    if pp:
        return {"salvaged_pp": pp}
    return None  # discard



def find_split(headline):
    """
    Apply Daniel's split rule with bad-pair recovery. Returns
    {subject, verb, predicate} or None.

    Walk verbs left to right. A candidate verb is REJECTED if:
      - it is the first word (no subject before it), or
      - it + the immediately following word form a listed BAD PAIR
        (meaning the candidate was really a noun, e.g. "report shows").
    On rejection, advance to the NEXT verb and test again (Daniel's recovery
    rule: a bad pair re-points the split to the second verb rather than
    discarding). Discard only if no candidate survives.
    """
    words = headline.split()
    verb_indices = [i for i, w in enumerate(words) if normalize(w) in VERB_SET]

    if not verb_indices:
        return None  # no verb at all -> discard

    cut = None
    for idx in verb_indices:
        if idx == 0:
            continue  # verb is first word -> no subject; try next verb
        # bad-pair check: chosen verb + next word
        if idx + 1 < len(words):
            pair = (normalize(words[idx]), normalize(words[idx + 1]))
            if pair in BAD_PAIRS:
                continue  # first word was a noun -> advance to next verb
        cut = idx
        break

    if cut is None or cut == 0:
        return None  # nothing splittable left -> discard

    subject = " ".join(words[:cut])
    verb = words[cut]
    predicate = " ".join(words[cut:])  # verb + everything after travels together
    return {"subject": subject, "verb": verb, "predicate": predicate}


def is_plural(subject):
    """Heuristic number agreement for the NEW subject (drives re-inflection)."""
    s = subject.lower().strip()
    if " and " in s:
        return True
    for lead in ("several ", "many ", "both ", "all ", "some ", "most ", "few ", "two ",
                 "three ", "four ", "five "):
        if s.startswith(lead):
            return True
    last = normalize(subject.split()[-1]) if subject.split() else ""
    if last.endswith("s") and not last.endswith("ss") and len(last) > 3:
        return True
    return False


def reinflect_verb(verb, subject_is_plural):
    """
    LemmInflect handles the form change. Lemmatize the moved verb to its base,
    then inflect for the new subject's number.
      - Plural subject  -> base form (VBP):  'announces' -> 'announce'
      - Singular subject -> 3rd-sing (VBZ):  'announce'  -> 'announces'
    Past-tense / participle forms (-ed, -ing) are left as-is: they don't agree.
    """
    raw = verb
    bare = normalize(verb)
    if not bare:
        return raw

    # Leave non-agreeing forms untouched (past, gerund/participle).
    if bare.endswith("ing") or bare.endswith("ed"):
        return raw

    # Special-case the copula/auxiliaries LemmInflect won't reshape the way we want.
    cop = {
        ("is", True): "are", ("are", False): "is",
        ("was", True): "were", ("were", False): "was",
        ("has", True): "have", ("have", False): "has",
    }
    key = (bare, subject_is_plural)
    if key in cop:
        return _preserve_caps(raw, cop[key])

    lemmas = getLemma(bare, upos="VERB")
    base = lemmas[0] if lemmas else bare

    tag = "VBP" if subject_is_plural else "VBZ"
    forms = getInflection(base, tag=tag)
    out = forms[0] if forms else base
    return _preserve_caps(raw, out)


def _preserve_caps(original, replacement):
    """Keep leading capitalization of the original surface form."""
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


# ---------------------------------------------------------------------------
# Defamation screen — reject a finished cross when a serious-accusation verb
# lands on a subject that looks like a real, named person. Keeps the verbs
# available for harmless/absurd crosses (nations, abstractions); screens only
# the case that manufactures a false accusation against an identifiable person.
# Conservative by design: over-rejecting a borderline real headline is the
# correct way to err for a safety screen.
# ---------------------------------------------------------------------------
ACCUSATION_VERBS = {
    "rape", "raped", "rapes", "raping",
    "molest", "molested", "molests", "molesting",
    "murder", "murders", "murdered",
    "assault", "assaults", "assaulted",
    "abuse", "abuses", "abused",
}

# Common capitalized sentence-openers that are NOT personal names; a single
# one of these leading the subject should not, by itself, trip person-detection.
_NON_NAME_CAPS = {
    "the", "a", "an", "this", "that", "these", "those", "new", "former",
    "us", "uk", "eu", "un", "world", "police", "scientists", "researchers",
    "officials", "voters", "leaders", "humans", "court", "courts",
}

def looks_like_person(subject):
    """
    Heuristic person-detector. Returns True when the subject plausibly names a
    specific individual who could be defamed:
      - two+ consecutive capitalized words (first + last name), OR
      - a single capitalized token that is not a common non-name opener.
    Deliberately broad: a safety screen should over-trigger, not under-trigger.
    """
    words = subject.split()
    if not words:
        return False
    for i in range(len(words) - 1):
        if words[i][:1].isupper() and words[i + 1][:1].isupper():
            return True
    if len(words) >= 1 and words[0][:1].isupper():
        if normalize(words[0]) not in _NON_NAME_CAPS:
            return True
    return False

def is_defamatory(headline, subject):
    """
    Reject if a serious-accusation verb appears in the PREDICATE portion and
    the subject looks like a named person. The accusation verb pinned to a real
    name is exactly the defamation risk we screen out.
    """
    if not looks_like_person(subject):
        return False
    pred_words = {normalize(w) for w in headline.split()[len(subject.split()):]}
    return bool(pred_words & {normalize(v) for v in ACCUSATION_VERBS})


def remix(parsed, n=None, seed=None, pp_swap=True, pp_swap_rate=0.5):
    """
    Assembly stage with the full chain:
      1. Clean predicates: keep clean ones; harvest a trailing PP from any
         poisoned by an interior bad pair (Daniel's salvage rule); discard
         poisoned predicates with no salvageable PP.
      2. Random subject + random clean predicate from DIFFERENT headlines,
         re-inflecting the predicate's lead verb to the new subject's number.
      3. PP-swap (optional): with probability pp_swap_rate, detach the new
         headline's own trailing PP and replace it with one drawn from the PP
         pool (which includes salvaged PPs + PPs harvested from good predicates).
    """
    if seed is not None:
        random.seed(seed)

    # ---- 1. clean predicates, build pools -------------------------------
    clean_predicates = []   # full fragments with usable predicates
    pp_pool = []            # free-floating trailing prepositional phrases
    subjects = []
    for p in parsed:
        subjects.append(p["subject"])
        result = clean_predicate(p)
        if result is None:
            continue                       # poisoned, no PP -> discarded
        if "salvaged_pp" in result:
            pp_pool.append(result["salvaged_pp"])   # poisoned but PP rescued
            continue
        clean_predicates.append(result)    # clean predicate, usable
        # also harvest this good predicate's own trailing PP for the swap pool
        pp = extract_trailing_pp(result["predicate"])
        if pp:
            pp_pool.append(pp)

    if not clean_predicates:
        return []

    # ---- 2 & 3. assemble -------------------------------------------------
    n = len(subjects) if n is None else min(n, len(subjects))
    out = []
    for i in range(n):
        subj = subjects[i]
        # predicate from a DIFFERENT headline where possible
        choices = [p for p in clean_predicates if p["subject"] != subj]
        if not choices:
            choices = clean_predicates
        pred = random.choice(choices)

        plural = is_plural(subj)
        new_verb = reinflect_verb(pred["verb"], plural)
        rest = pred["predicate"].split()[1:]
        new_pred = " ".join([new_verb] + rest)
        headline = f"{subj} {new_pred}"

        # PP-swap: replace this headline's trailing PP with a pooled one.
        # GUARD: only swap when a verb remains in the stem AFTER removing the
        # trailing PP, so the swap can never produce a verbless headline.
        if pp_swap and pp_pool and random.random() < pp_swap_rate:
            own_pp = extract_trailing_pp(headline)
            if own_pp:
                stem = headline[: headline.rfind(own_pp)].rstrip()
                stem_words = stem.split()
                # the subject is words[:?]; require at least one VERB in the stem
                # beyond the subject, i.e. the stem must contain a verb-set word
                # that is NOT inside the subject span.
                subj_len = len(subj.split())
                stem_has_verb = any(
                    normalize(w) in VERB_SET for w in stem_words[subj_len:]
                )
                # also require the stem to be more than just the bare subject
                if stem_has_verb and len(stem_words) > subj_len:
                    swap_in = random.choice(
                        [p for p in pp_pool if p != own_pp] or pp_pool
                    )
                    headline = f"{stem} {swap_in}"

        if is_defamatory(headline, subj):
            continue   # safety screen: no accusation pinned to a named person
        out.append(headline)
    return out


if __name__ == "__main__":
    # Test batch: real-ish headlines spanning the tricky cases.
    test = [
        "Scientists discover new species in Amazon rainforest",
        "Stock market reaches record high amid economic optimism",
        "City council approves funding for new public library",
        "Police report shows sharp decline in downtown crime",      # 'report' noun trap
        "Mayor unveils plan to reduce traffic congestion",
        "University researchers develop new cancer treatment",
        "Climate study warns of accelerating ice loss",             # 'study' neverVerb in V13
        "Voters head to polls for important referendum",
        "Officials report a surge in seasonal flu cases",           # 'report' as real verb
        "Tech company announces breakthrough in AI research",
        "Breaking news shocks investors worldwide",                 # verb-ish first word
        "Local restaurant wins prestigious culinary award",
    ]

    print("=== SPLITS ===")
    parsed = []
    for h in test:
        r = find_split(h)
        if r is None:
            print(f"  [DISCARD] {h}")
        else:
            parsed.append(r)
            print(f"  SUBJ: {r['subject']!r:45}  VERB: {r['verb']!r:14}  PRED: {r['predicate']!r}")

    print("\n=== REMIX (seed=7) ===")
    for line in remix(parsed, seed=7):
        print("  " + line)
