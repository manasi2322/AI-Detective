"""Command line: python -m detective <command> <case_dir> ...

  timeline  <case> [--records | --claims] [--person NAME]
  search    <case> "query" [--person NAME] [-k N]
  entities  <case>
  add --llm to any command to also run Claude extraction (needs the anthropic SDK + credentials).
"""

from __future__ import annotations

import argparse
import sys

from .loader import load_case
from .models import EvidenceKind
from .pipeline import investigate
from .timeline import Timeline


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="detective", description="AI Detective - evidence explorer")
    ap.add_argument("command", choices=["timeline", "search", "entities"])
    ap.add_argument("case_dir")
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--person")
    ap.add_argument("-k", type=int, default=5)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--records", action="store_true", help="only hard records")
    group.add_argument("--claims", action="store_true", help="only witness claims")
    ap.add_argument("--llm", action="store_true", help="also extract events with Claude")
    args = ap.parse_args(argv)

    case = load_case(args.case_dir)
    propose = None
    if args.llm:
        from .anthropic_backend import make_claude_proposer

        propose = make_claude_proposer()
    inv = investigate(case, propose)
    print(f"# {case.title}  ({case.difficulty}, {len(case.documents)} documents)\n")

    if args.command == "timeline":
        tl = inv.timeline
        if args.person:
            tl = Timeline(tl.for_person(args.person))
        kinds = {EvidenceKind.RECORD} if args.records else {EvidenceKind.CLAIM} if args.claims else None
        print(tl.render(kinds))
        if inv.index.rejections:
            print(f"\n{len(inv.index.rejections)} LLM proposals rejected as ungrounded:")
            for r in inv.index.rejections:
                print(f"  - [{r.doc_id}] {r.reason}: {r.item.get('quote', '')!r}")
    elif args.command == "search":
        if not args.query and not args.person:
            ap.error("search needs a query or --person")
        for hit in inv.store.search(args.query, k=args.k, person=args.person):
            print(f"{hit.score:5.2f}  [{hit.quote.cite()}] ({hit.doc_type})  \"{hit.quote.text}\"")
    else:
        for name, mentions in inv.index.mentions.items():
            if not mentions:
                continue
            docs = sorted({m.quote.doc_id for m in mentions})
            print(f"{name:<18} {mentions[0].entity_type:<8} {len(mentions):>3} mentions in {', '.join(docs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
