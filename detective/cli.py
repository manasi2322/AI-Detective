"""Command line: python -m detective <command> <case_dir> ...

  timeline  <case> [--records | --claims] [--person NAME]
  search    <case> "query" [--person NAME] [-k N]
  entities  <case>
  alibis    <case> [--person NAME]   every whereabouts claim checked against badge log + CCTV
  speculation <case>                 guesses and impressions, flagged so they are not used as evidence
  opportunity <case>                 who records put at the scene during the crime window
  analyze   <case>                   alibis + speculation + opportunity
  motives   <case>                   reasons to act, with who said them
  links     <case>                   CCTV matches (assumptions), hidden connections, disputed badges
  investigate <case> [--llm]         reasoning log per suspect, scores, most likely suspect
  report    <case> [--out FILE]      full Markdown case report; every citation checked against the sources
  evaluate  [cases_dir] [-v]         score every case against its answer key
  ask       <case> "question" [--llm] follow-up question, answered with checked citations
  reassess  <case> [--add FILE ...]  add evidence (or uncover the next stage) and show what changed
  chat      <case>                   interactive: questions, :uncover, :add FILE, :report
  web       [cases_dir] [--port N]   local web UI at http://127.0.0.1:8000
  llm-run   [cases_dir]              live Claude run on every case; records accepted/rejected items
  --stage N on any case command uses only the evidence uncovered up to stage N.
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
    ap.add_argument("command", choices=["timeline", "search", "entities", "alibis", "speculation", "opportunity", "analyze", "motives", "links", "investigate", "report", "evaluate", "ask", "reassess", "chat", "web", "llm-run"])
    ap.add_argument("case_dir", nargs="?")
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--person")
    ap.add_argument("-k", type=int, default=5)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--records", action="store_true", help="only hard records")
    group.add_argument("--claims", action="store_true", help="only witness claims")
    ap.add_argument("--llm", action="store_true", help="also extract events with Claude")
    ap.add_argument("--stage", type=int, help="only evidence uncovered up to this stage")
    ap.add_argument("--out", help="report: write to this file instead of printing")
    ap.add_argument("-v", "--verbose", action="store_true", help="evaluate: list every check")
    ap.add_argument("--port", type=int, default=8000, help="web: port to listen on")
    ap.add_argument("--add", nargs="+", default=[], metavar="FILE", help="reassess: evidence documents to add")
    args = ap.parse_args(argv)

    if args.command == "evaluate":
        from .evaluate import evaluate_all, render

        results = evaluate_all(args.case_dir or "cases")
        print(render(results, args.verbose))
        return 0 if all(r.solved for r in results) else 1
    if args.command == "llm-run":
        from .llm_run import check_credentials, run_all, summarise

        problem = check_credentials()
        if problem:
            print(problem)
            return 2
        print(summarise(run_all(args.case_dir or "cases")))
        print("Details written to samples/llm_runs/.")
        return 0
    if args.command == "web":
        from .web import serve

        server = serve(args.case_dir or "cases", args.port)
        print(f"AI Detective web UI: http://127.0.0.1:{server.server_address[1]}  (Ctrl+C to stop)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0
    if not args.case_dir:
        ap.error("case_dir is required")
    if args.command == "chat":
        from .chat import run_chat

        answerer = None
        if args.llm:
            from .anthropic_backend import make_claude_answerer

            answerer = make_claude_answerer()

        def lines():
            while True:
                try:
                    yield input("detective> ")
                except EOFError:
                    return

        run_chat(args.case_dir, lines(), stage=args.stage, answerer=answerer)
        return 0
    if args.command == "reassess":
        from .chat import Session

        session = Session(args.case_dir, stage=args.stage)
        if args.add:
            for path in args.add:
                print(session.add(open(path, encoding="utf-8").read(), path))
                print()
        else:
            print(session.uncover())
        return 0
    case = load_case(args.case_dir, stage=args.stage)
    propose = investigator = None
    if args.llm and args.command == "ask":
        pass  # ask --llm uses Claude to phrase the answer, below
    elif args.llm:
        from .anthropic_backend import make_claude_investigator, make_claude_proposer

        propose = make_claude_proposer()
        if args.command == "investigate":
            investigator = make_claude_investigator()
    inv = investigate(case, propose, investigator)
    if args.command != "report":
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
    elif args.command == "ask":
        if not args.query:
            ap.error('ask needs a question, e.g. ask cases/case1_missing_laptop "Did Marcus lie?"')
        from .qa import answer_with_llm, ask

        if args.llm:
            from .anthropic_backend import make_claude_answerer

            print(answer_with_llm(inv, args.query, make_claude_answerer()).render())
        else:
            print(ask(inv, args.query).render())
    elif args.command == "motives":
        print(render_motives(inv))
    elif args.command == "links":
        print(render_links(inv))
    elif args.command == "investigate":
        print(render_investigation(inv, args.person))
    elif args.command == "report":
        from .loader import case_stages
        from .report import build_report

        stages = case_stages(args.case_dir)
        earlier = None
        if args.stage is None and len(stages) > 1:
            earlier = investigate(load_case(args.case_dir, stage=stages[0]))
        text = build_report(inv, earlier)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"Report written to {args.out} (all citations checked).")
        else:
            print(text)
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


def render_motives(inv) -> str:
    out = ["== MOTIVES: reasons to act (guesses are excluded) =="]
    for m in inv.motives:
        out.append(f"  {m.person}: {m.describe()}")
        out.append(f"       \"{m.quote.text}\"  [{m.quote.cite()}]")
    if not inv.motives:
        out.append("  (none)")
    return "\n".join(out) + "\n"


def render_links(inv) -> str:
    out = ["== CCTV MATCHES (assumptions, not identifications) =="]
    for m in inv.cctv_matches:
        out.append(f"  [{m.cctv.cite()}] -> {m.person or 'no match'}  ({m.label.upper()})")
        out.append(f"       \"{m.cctv.text}\"")
        out.append(f"       why: {m.explanation()}")
    if not inv.cctv_matches:
        out.append("  (no unnamed people on CCTV)")
    out.append("\n== HIDDEN CONNECTIONS with outside parties ==")
    for c in inv.connections:
        out.append(f"  {c.suspect} <-> {c.party}: {c.explanation()}")
        for q in c.messages:
            out.append(f"       message: \"{q.text}\"  [{q.cite()}]")
        if c.denial:
            out.append(f"       denial:  \"{c.denial.text}\"  [{c.denial.cite()}]")
    if not inv.connections:
        out.append("  (none)")
    out.append("\n== DISPUTED RECORDS (left out of alibi and opportunity checks) ==")
    for d in inv.disputes:
        out.append(f"  {d.explanation}")
    if not inv.disputes:
        out.append("  (none: every badge/login record agrees with CCTV)")
    return "\n".join(out) + "\n"


def render_investigation(inv, person: str | None = None) -> str:
    a = inv.assessment
    out = ["== INVESTIGATION: reasoning log per suspect ==",
           "   labels: FACT (records) / CLAIM (statements) / ASSUMPTION (inference) / SPECULATION (weighs 0)"]
    for log in a.ranking():
        if person and log.suspect != person:
            continue
        out.append(f"\n{log.suspect}: score {log.score:+.1f}")
        for s in log.steps:
            src = " [llm]" if s.source == "llm" else ""
            out.append(f"  {s.weight:+.1f}  {s.label.value.upper():<11} {s.kind}{src}: {s.text}")
            if s.tested:
                out.append(f"          tested: \"{s.tested.text}\"  [{s.tested.cite()}]")
            for q in s.evidence:
                if q != s.tested:
                    out.append(f"          cites:  \"{q.text}\"  [{q.cite()}]")
    level, why = a.confidence()
    out.append("\n== CONCLUSION ==")
    out.append("  ranking: " + ", ".join(f"{l.suspect} {l.score:+.1f}" for l in a.ranking()))
    out.append(f"  most likely: {a.most_likely}  (confidence: {level}; {why})")
    if a.rejections:
        out.append(f"\n{len(a.rejections)} LLM steps rejected:")
        for r in a.rejections:
            out.append(f"  - {r.reason}: {r.item.get('reasoning', '')!r}")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    sys.exit(main())
