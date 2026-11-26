"""Deterministic directory-name routing; no provider calls or political classifications."""
import re
import unicodedata


def folded(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))


def scope_response(question, selected, directory):
    text = folded(question)
    matches = set()
    spans = []
    for senator in directory:
        names = {senator['name'], senator.get('official_name', senator['name'])}
        # Quoted nicknames are supplied by the dated directory, not inferred biographies.
        official = senator.get('official_name', senator['name'])
        nick = re.search('[“"]([^”"]+)[”"]', official)
        if nick:
            names.add(nick[1] + ' ' + senator['name'].split()[-1])
            names.add(re.sub('[“"][^”"]+[”"]\\s*', '', official).strip())
            names.add(official.split()[0] + ' ' + senator['name'].split()[-1])
        for name in names:
            for match in re.finditer(r'(?<!\w)' + re.escape(folded(name)) + r'(?!\w)', text):
                matches.add(senator['id'])
                spans.append(match.span())
    remainder = list(text)
    for start, end in spans:
        remainder[start:end] = ' ' * (end - start)
    remainder = ''.join(remainder)
    surnames = {}
    for senator in directory:
        # IDs preserve multiword surnames better than the last display-name token.
        surname = senator['name'].split()[-1]
        if surname in {'III', 'IV', 'Jr.'}:
            surname = senator['name'].split()[-2]
        surnames.setdefault(folded(surname), []).append(senator['id'])
    ambiguous = []
    for surname, ids in surnames.items():
        if surname == 'go':
            pattern = r'\b(?:senator|sen\.?|bong)\s+go\b'
        else:
            pattern = r'(?<!\w)' + re.escape(surname) + r'(?!\w)'
        if re.search(pattern, remainder):
            if len(ids) > 1:
                ambiguous.extend(ids)
            else:
                matches.update(ids)
    others = matches - {selected['id']}
    comparison = bool(re.search(r'\b(compare|comparison|versus|vs|ihambing|kumpara|paghambingin)\b', text))
    if not others and not ambiguous and not comparison:
        return None
    targets = [s for s in directory if s['id'] in (others | set(ambiguous))]
    if ambiguous:
        answer = 'Which senator do you mean: ' + ', '.join(s['name'] for s in targets) + '? Please use a full name.'
        kind = 'CLARIFY_SUBJECT'
    elif comparison or len(others) > 1:
        answer = f"This chat focuses on Senator {selected['name']}. Please ask about one senator at a time. The Compare page does not yet provide sourced comparisons."
        kind = 'SINGLE_SUBJECT_SCOPE'
    else:
        answer = f"This chat focuses on Senator {selected['name']}. To ask about Senator {targets[0]['name']}, please switch to their chat."
        kind = 'SWITCH_SUBJECT'
    return {'type': kind, 'label': 'CHAT SCOPE', 'answer': answer, 'topic': 'scope',
            'citations': [], 'retrieval_count': 0, 'switch_targets': [{'id': s['id'], 'name': s['name']} for s in targets],
            'limitation': 'Each question must stand on its own. Switching does not transfer messages or submit your question.',
            'validation': {'status': kind, 'verified': False, 'citation_ids': []}}
