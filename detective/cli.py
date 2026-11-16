"""Command line: python -m detective <command> <case_dir> ...

  timeline  <case> [--records | --claims] [--person NAME]
  search    <case> "query" [--person NAME] [-k N]
  entities  <case>
  alibis    <case> [--person NAME]   every whereabouts claim checked against badge log + CCTV
  speculation <case>                 guesses and impressions, flagged so they are not used as evidence
  opportunity <case>                 who records put at the scene during the crime window
  analyze   <case>                   alibis + speculation + opportunity
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
    ap.add_argument("command", choices=["timeline", "search", "entities", "alibis", "speculation", "opportunity", "analyze"])
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
    elif args.command in ("alibis", "speculation", "opportunity", "analyze"):
        if args.command in ("alibis", "analyze"):
            print(render_alibis(inv, args.person))
        if args.command in ("speculation", "analyze"):
            print(render_speculation(inv))
        if args.command in ("opportunity", "analyze"):
            print(render_opportunity(inv))
    else:
        for name, mentions in inv.index.mentions.items():
            if not mentions:
                continue
            docs = sorted({m.quote.doc_id for m in mentions})
            print(f"{name:<18} {mentions[0].entity_type:<8} {len(mentions):>3} mentions in {', '.join(docs)}")
    return 0


MARK = {"supported": "OK ", "consistent": "~  ", "unverified": "?  ", "contradicted": "XX "}


def render_alibis(inv, person: str | None = None) -> str:
    out = ["== ALIBIS: whereabouts claims vs badge log / CCTV =="]
    for name, alibi in inv.alibis.items():
        if not alibi.checks or (person and name != person):
            continue
        suspect = next(p.suspect for p in inv.index.case.people if p.name == name)
        out.append(f"\n{name}{' (suspect)' if suspect else ''}: alibi {alibi.status.upper()}")
        for c in alibi.checks:
            out.append(f"  {MARK[c.verdict.value]}{c.verdict.value.upper():<13}{c.claim.describe()}")
            out.append(f"       claim:  \"{c.claim.quote.text}\"  [{c.claim.quote.cite()}]")
            for q in c.evidence:
                out.append(f"       record: \"{q.text}\"  [{q.cite()}]")
            out.append(f"       why:    {c.explanation}")
            for a in c.assumptions:
                out.append(f"       assumes: {a}")
    return "\n".join(out) + "\n"


def render_speculation(inv) -> str:
    out = ["== SPECULATION: not evidence, never used as such =="]
    for s in inv.speculation:
        about = ", ".join(s.about) or "-"
        out.append(f"  {s.category.upper():<11}{s.speaker or '?'} about {about} (\"{s.marker}\")")
        out.append(f"             \"{s.quote.text}\"  [{s.quote.cite()}]")
    if not inv.speculation:
        out.append("  (none)")
    return "\n".join(out) + "\n"


def render_opportunity(inv) -> str:
    w = inv.window
    if w is None:
        return "== OPPORTUNITY ==\n  (case.json defines no scene/window)\n"
    out = [
        f"== OPPORTUNITY: window {w.describe()} ==",
        f"  opens:  \"{w.start_quote.text}\"  [{w.start_quote.cite()}]",
        f"  closes: \"{w.end_quote.text}\"  [{w.end_quote.cite()}]",
    ]
    for o in inv.opportunity.values():
        out.append(f"\n  {o.person}: {o.access.value.upper()}")
        out.append(f"       why:    {o.explanation}")
        for q in o.evidence:
            out.append(f"       record: \"{q.text}\"  [{q.cite()}]")
        for a in o.assumptions:
            out.append(f"       assumes: {a}")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    sys.exit(main())
