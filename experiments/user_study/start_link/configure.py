"""Build a nonsecret service config from Google Forms' Get pre-filled link."""
import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit, urlunsplit

from server import Config, SEQUENCES


def from_prefilled_link(link, origin):
    parts = urlsplit(link.strip())
    query = parse_qs(parts.query, keep_blank_values=True)
    fields = {key: values for key, values in query.items() if key.startswith('entry.')}
    if len(fields) != 2 or any(len(values) != 1 for values in fields.values()):
        raise ValueError('Prefill only Participant ID and Assigned sequence')
    ids = [key for key, values in fields.items() if values == ['TEST-LINK']]
    orders = [key for key, values in fields.items() if values[0] in SEQUENCES]
    if len(ids) != 1 or len(orders) != 1:
        raise ValueError('Use TEST-LINK for the ID and one of the four exact study sequences')
    return Config(origin, urlunsplit((parts.scheme, parts.netloc, parts.path, '', '')),
                  ids[0], orders[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefilled_link_file', type=Path)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = from_prefilled_link(args.prefilled_link_file.read_text(encoding='utf-8'), args.origin)
    # Avoid replacing a live configuration accidentally.
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(config.__dict__, output, indent=2)
        output.write('\n')


if __name__ == '__main__':
    main()
