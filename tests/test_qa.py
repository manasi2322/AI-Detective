import pytest

from detective.grounding import verify
from detective.qa import answer_with_llm, ask
from detective.report import check_citations


def test_did_the_liar_lie(inv1):
    a = ask(inv1, "Did Marcus lie?")
    assert a.intent == "lie" and a.text.startswith("Yes. 2 statements")
    cited = {q.cite() for _, q in a.citations}
    assert {"interview_marcus:L2", "badge_log:L6", "interview_marcus:L6", "chat_marcus_alex:L1"} <= cited


def test_honest_suspect_did_not_lie_but_unconfirmable_parts_are_flagged(inv1):
    a = ask(inv1, "did sam lie")  # lower case, no question mark
    assert a.text.startswith("No.") and "could still be false" in a.text


def test_a_friend_who_gave_a_false_alibi_is_caught(inv2):
    a = ask(inv2, "Is Celia telling the truth?")
    assert a.text.startswith("Yes.") and "wifi_log:L1" in {q.cite() for _, q in a.citations}


def test_where_was_someone_separates_records_statements_and_assumptions(inv1):
    a = ask(inv1, "Where was Marcus at 19:45?")
    assert "records put Marcus Hale on the premises" in a.text
    kinds = {k for k, _ in a.citations}
    assert kinds == {"record", "statement", "assumption"}


def test_where_mentions_a_disputed_record_but_does_not_use_it(inv3):
    a = ask(inv3, "Where was Iris at 22:15?")
    assert "Set aside" in a.text and "login_log:L1" in a.text
    assert "on the premises" in a.text


def test_who_was_at_a_place(inv1):
    a = ask(inv1, "Who was in the Design Lab at 20:50?")
    assert "Lena Torres at 03-12 20:47" in a.text and "Marcus" not in a.text


def test_unknown_person_is_not_invented(inv1):
    a = ask(inv1, "Where was Ruth at 23:40?")
    assert a.text.startswith("Nobody called Ruth appears in this case") and not a.citations


@pytest.mark.parametrize("question", [
    "Who did it?", "How confident are you?", "What is Marcus's motive?", "Is Priya's alibi solid?",
    "Why not Lena?", "Who had the opportunity?", "Who is Marcus connected to?", "What contradictions are there?",
    "What happened at 19:58?", "Was the drawer forced?",
])
def test_every_answer_is_grounded(inv1, question):
    a = ask(inv1, question)
    assert a.text and a.intent
    assert all(verify(inv1.index.case, q) for _, q in a.citations)
    assert check_citations(inv1.index.case, a.render()).ok


def test_unrecognised_question_falls_back_to_search_without_concluding(inv1):
    a = ask(inv1, "Was the drawer forced?")
    assert a.intent == "search" and "no conclusion is drawn" in a.text
    assert "interview_daniel:L6" in {q.cite() for _, q in a.citations}


def test_llm_answer_keeps_real_quotes_and_drops_invented_ones(inv1):
    def fake(question, evidence, rules_answer):
        assert "badge_log" in evidence
        return {"answer": "Yes: he said he never came back, but he badged in at 19:41.",
                "quotes": [{"doc": "badge_log", "text": "2026-03-12 19:41 | Marcus Hale | Main Entrance | ENTRY"},
                           {"doc": "badge_log", "text": "2026-03-12 23:59 | Marcus Hale | Design Lab | EXIT"}]}
    a = answer_with_llm(inv1, "Did Marcus lie?", fake)
    assert a.source == "llm" and [q.cite() for _, q in a.citations] == ["badge_log:L6"]
    assert len(a.rejected) == 1 and "23:59" in a.rejected[0]


def test_llm_answer_with_no_real_quotes_falls_back_to_rules(inv1):
    a = answer_with_llm(inv1, "Did Marcus lie?", lambda *_: {"answer": "Yes.", "quotes": [{"doc": "x", "text": "y"}]})
    assert a.source == "rules" and a.text.startswith("(The LLM answer had no verifiable quotes")
