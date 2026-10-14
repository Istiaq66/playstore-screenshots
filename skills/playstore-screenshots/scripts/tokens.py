"""Token usage and estimated cost of a Claude Code run, read from the session log.

usage:
  python tokens.py start            mark the start of a run (call first)
  python tokens.py report           totals since the mark (subagents included)
  python tokens.py report --all     totals for the whole session
Options: --project DIR (default: current directory), --session FILE.jsonl

Claude Code writes every API response, with its `usage`, to
~/.claude/projects/<project>/<session>.jsonl (subagents in <session>/subagents/).
The newest log of the project is the running session.

Cost is the API-list-price equivalent. On a Claude subscription you aren't
billed per token; the figure shows what the run would cost on the API.
"""
import argparse, glob, json, os, re, sys, tempfile
from datetime import datetime, timezone

# $ per million tokens: (input, output, cache-read multiplier of input).
# Cache writes: 1.25x input (5-minute TTL), 2x input (1-hour TTL).
# Source: Anthropic model pricing, cached 2026-09-25. Check the pricing page before relying on it.
PRICES = {
    'claude-fable-5-1': (10.00, 50.00, 0.025),
    'claude-mythos-5-1': (10.00, 50.00, 0.025),
    'claude-fable-5': (10.00, 50.00, 0.10),
    'claude-opus-5-5': (4.00, 20.00, 0.05),
    'claude-opus-5': (5.00, 25.00, 0.10),
    'claude-opus-4-8': (5.00, 25.00, 0.10),
    'claude-opus-4-7': (5.00, 25.00, 0.10),
    'claude-opus-4-6': (5.00, 25.00, 0.10),
    'claude-sonnet-5-5': (2.00, 10.00, 0.10),
    'claude-sonnet-5': (2.00, 10.00, 0.10),
    'claude-sonnet-4-6': (3.00, 15.00, 0.10),
    'claude-haiku-4-5': (1.00, 5.00, 0.10),
}
PRICES_AS_OF = '2026-09-25'
MARK = os.path.join(tempfile.gettempdir(), 'playstore-screenshots-tokens.json')


def price_for(model):
    model = re.sub(r'-\d{8}$', '', model or '')  # drop date suffixes
    if model in PRICES:
        return PRICES[model]
    for key in sorted(PRICES, key=len, reverse=True):  # e.g. a "[1m]" variant
        if model.startswith(key):
            return PRICES[key]
    return None


def project_dir(path):
    slug = re.sub(r'[^A-Za-z0-9]', '-', os.path.abspath(path))
    return os.path.join(os.path.expanduser('~'), '.claude', 'projects', slug)


def current_session(project):
    logs = glob.glob(os.path.join(project_dir(project), '*.jsonl'))
    if not logs:
        sys.exit(f'no Claude Code session logs in {project_dir(project)}')
    return max(logs, key=os.path.getmtime)


def parse_ts(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def usage_rows(session, since):
    files = [session] + glob.glob(os.path.join(session[:-len('.jsonl')], 'subagents', '*.jsonl'))
    seen = set()
    for f in files:
        for line in open(f, encoding='utf-8'):
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if o.get('type') != 'assistant':
                continue
            m = o.get('message') or {}
            u, mid = m.get('usage'), m.get('id')
            if not u or mid in seen:  # one response is logged once per content block
                continue
            if since and o.get('timestamp') and parse_ts(o['timestamp']) < since:
                continue
            seen.add(mid)
            yield m.get('model', '?'), u


def report(session, since):
    totals = {}
    for model, u in usage_rows(session, since):
        t = totals.setdefault(model, dict(calls=0, input=0, write5m=0, write1h=0, read=0, output=0))
        cc = u.get('cache_creation') or {}
        w1h = cc.get('ephemeral_1h_input_tokens', 0)
        w5m = cc.get('ephemeral_5m_input_tokens', u.get('cache_creation_input_tokens', 0) - w1h)
        t['calls'] += 1
        t['input'] += u.get('input_tokens', 0)
        t['write5m'] += w5m
        t['write1h'] += w1h
        t['read'] += u.get('cache_read_input_tokens', 0)
        t['output'] += u.get('output_tokens', 0)

    if not totals:
        print('no API calls recorded in that window')
        return
    print(f"{'model':<20}{'calls':>6}{'input':>10}{'cache write':>13}{'cache read':>13}{'output':>10}{'est. $':>10}")
    grand, unknown = 0.0, []
    for model, t in sorted(totals.items()):
        p = price_for(model)
        cost = None
        if p:
            inp, out, read_x = p
            cost = (t['input'] * inp + t['write5m'] * inp * 1.25 + t['write1h'] * inp * 2
                    + t['read'] * inp * read_x + t['output'] * out) / 1e6
            grand += cost
        else:
            unknown.append(model)
        writes = t['write5m'] + t['write1h']
        print(f"{model:<20}{t['calls']:>6}{t['input']:>10,}{writes:>13,}{t['read']:>13,}{t['output']:>10,}"
              f"{('$%.2f' % cost) if cost is not None else 'n/a':>10}")
    total_tokens = sum(t['input'] + t['write5m'] + t['write1h'] + t['read'] + t['output'] for t in totals.values())
    print(f'total {total_tokens:,} tokens, est. ${grand:.2f} at API list prices ({PRICES_AS_OF})')
    if unknown:
        print('no price for: ' + ', '.join(unknown) + ' (not included in $)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['start', 'report'])
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--project', default=os.getcwd())
    ap.add_argument('--session')
    a = ap.parse_args()
    session = a.session or current_session(a.project)

    if a.cmd == 'start':
        now = datetime.now(timezone.utc).isoformat()
        json.dump({'session': session, 'since': now}, open(MARK, 'w'))
        print(f'token count started {now} for {os.path.basename(session)}')
        return

    since = None
    if not a.all and os.path.exists(MARK):
        mark = json.load(open(MARK))
        if mark['session'] == session:
            since = parse_ts(mark['since'])
    print(f"session {os.path.basename(session)}, {'since ' + since.isoformat() if since else 'whole session'}")
    report(session, since)


if __name__ == '__main__':
    main()
