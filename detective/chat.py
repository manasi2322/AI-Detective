"""Interactive investigation: ask follow-up questions, uncover or add evidence, and see what changes.

    python -m detective chat cases/case3_leaked_formula --stage 1

Commands inside the chat:
    any question            e.g. "Did Noah lie?", "Where was Iris at 22:15?"
    :uncover                reveal the case's next evidence stage and reassess
    :add FILE               add an evidence document (front matter + text) and reassess
    :who                    current ranking and confidence
    :report [FILE]          write the full case report (citations checked)
    :help  :quit
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from .loader import add_evidence, case_stages, document_from_text, load_case
from .pipeline import investigate
from .qa import Answerer, answer_with_llm, ask
from .reassess import compare
from .report import build_report

HELP = __doc__.split("Commands inside the chat:")[1].strip("\n")


class Session:
    """The state of one investigation: a case, its current evidence, and the latest results."""

    def __init__(self, case_dir: str | Path, stage: int | None = None, answerer: Answerer | None = None):
        self.case_dir = Path(case_dir)
        self.stages = case_stages(case_dir)
        self.stage = stage if stage is not None else self.stages[-1]
        self.extra = []  # documents added by the investigator
        self.answerer = answerer
        self.history = []  # earlier investigations, oldest first
        self.inv = self._run()

    def _run(self):
        case = load_case(self.case_dir, stage=self.stage)
        if self.extra:
            case = add_evidence(case, self.extra)
        return investigate(case)

    def ask(self, question: str) -> str:
        if self.answerer is not None:
            return answer_with_llm(self.inv, question, self.answerer).render()
        return ask(self.inv, question).render()

    def uncover(self) -> str:
        later = [s for s in self.stages if s > self.stage]
        if not later:
            return "There is no more evidence to uncover in this case."
        self.stage = later[0]
        return self._reassess()

    def add(self, raw: str, name: str = "<new evidence>") -> str:
        doc = document_from_text(raw, name)
        self.extra.append(doc)
        try:
            return self._reassess()
        except Exception:
            self.extra.pop()
            raise

    def _reassess(self) -> str:
        before = self.inv
        after = self._run()
        self.history.append(before)
        self.inv = after
        return compare(before, after).render()

    def ranking(self) -> str:
        a = self.inv.assessment
        level, why = a.confidence()
        rows = [f"  {l.suspect:<20} {l.score:+.1f}" for l in a.ranking()]
        return "\n".join([f"Most likely: {a.most_likely} (confidence {level})", *rows, f"  {why}"])

    def report(self) -> str:
        return build_report(self.inv, self.history[0] if self.history else None)


def run_chat(case_dir: str | Path, lines: Iterable[str], write: Callable[[str], None] = print,
             stage: int | None = None, answerer: Answerer | None = None) -> Session:
    s = Session(case_dir, stage, answerer)
    case = s.inv.index.case
    write(f"Investigating: {case.title} ({case.difficulty}), {len(case.documents)} documents, "
          f"evidence stage {s.stage} of {s.stages[-1]}. Type :help for commands.\n")
    write(s.ranking())
    for line in lines:
        line = line.strip()
        if not line:
            continue
        cmd, _, arg = line.partition(" ")
        try:
            if cmd in (":quit", ":q", ":exit"):
                break
            elif cmd == ":help":
                write(HELP)
            elif cmd == ":who":
                write(s.ranking())
            elif cmd == ":uncover":
                write(s.uncover())
            elif cmd == ":add":
                path = Path(arg.strip())
                write(s.add(path.read_text(encoding="utf-8"), path))
            elif cmd == ":report":
                text = s.report()
                if arg.strip():
                    Path(arg.strip()).write_text(text, encoding="utf-8")
                    write(f"Report written to {arg.strip()} (all citations checked).")
                else:
                    write(text)
            elif cmd.startswith(":"):
                write(f"Unknown command {cmd}. Type :help.")
            else:
                write(s.ask(line))
        except (OSError, ValueError) as e:
            write(f"Error: {e}")
        write("")
    return s
