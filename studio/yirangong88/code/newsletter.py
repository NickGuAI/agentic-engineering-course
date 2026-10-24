"""Render a newsletter from manually verified web evidence; no network calls."""
import argparse
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def previous_day(as_of):
    moment = datetime.fromisoformat(as_of.replace('Z', '+00:00'))
    if moment.tzinfo is None:
        raise ValueError('Execution time must include a time zone')
    return (moment.astimezone(ZoneInfo('America/New_York')).date()
            - timedelta(days=1)).isoformat()


def render(data):
    target = previous_day(data['as_of'])
    selected, decisions = [], []
    seen = set()
    for item in data['candidates']:
        url = urlparse(item['url'])
        if url.scheme != 'https' or url.hostname not in {'openai.com', 'www.anthropic.com'}:
            raise ValueError('Unexpected source: ' + item['url'])
        if item['url'] in seen:
            raise ValueError('Duplicate candidate')
        seen.add(item['url'])
        keep = item['publisher_date'] == target
        decisions.append({'url': item['url'], 'date': item['publisher_date'],
                          'decision': 'include' if keep else 'outside target date'})
        if keep:
            for field in ('fact', 'product', 'engineering', 'evidence_location'):
                if not item.get(field):
                    raise ValueError('Missing verified editorial input: ' + field)
            selected.append(item)
    questions = data['questions']
    if len(questions) != 2 or not all(q.endswith('?') for q in questions):
        raise ValueError('Exactly two closing questions required')
    lines = [f'# AI news — {target}', '',
             f"- Executed: {data['as_of']}.",
             '- Window: previous calendar day in America/New_York, as clarified by the user.',
             '- Date convention: match the publisher’s displayed date. Exact publication times and publisher time zones were unavailable; these are not verified Eastern-time publication instants.',
             '- Coverage: the retrieved Anthropic News and OpenAI News indexes and linked matching articles.', '']
    for item in selected:
        lines.extend([f"## {item['title']}", '',
                      f"- **Reported:** {item['fact']} [Original post]({item['url']}).",
                      f"- **Product takeaway (inference):** {item['product']}",
                      f"- **Engineering takeaway (inference):** {item['engineering']}", ''])
    if not selected:
        lines.extend(['- No matching stories found in the supplied evidence.', ''])
    lines.extend([data['coverage_note'], '', '## Two questions', '',
                  f'1. {questions[0]}', f'2. {questions[1]}', ''])
    return '\n'.join(lines), decisions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--name', default='run-03')
    args = parser.parse_args()
    if not args.name.replace('-', '').isalnum():
        parser.error('Name must contain only letters, digits, and hyphens')
    raw = args.input.read_bytes()
    data = json.loads(raw)
    result, decisions = render(data)
    output = ROOT / 'outputs'
    targets = [output / (args.name + suffix) for suffix in ('.md', '-selection.json')]
    if any(p.exists() for p in targets):
        parser.error('Output already exists; choose a new name to preserve history')
    output.mkdir(exist_ok=True)
    targets[0].write_text(result)
    targets[1].write_text(json.dumps({'input_sha256': hashlib.sha256(raw).hexdigest(),
        'target_date': previous_day(data['as_of']), 'decisions': decisions}, indent=2) + '\n')
    print(f'Wrote {targets[0]}')


if __name__ == '__main__':
    main()
