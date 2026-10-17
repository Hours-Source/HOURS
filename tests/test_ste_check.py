"""utils/ste_check.py — the share of docstring sentences that meet the STE writing rules."""

import pytest

from utils.ste_check import judge, sentences


@pytest.mark.parametrize("doc, n_sentences, n_failing", [
    # Short, active sentences pass; inline code and decimals do not split a sentence.
    ("The levy moves TEH. It does not create it. `x.y` reads 0.40 here.", 3, 0),
    # Passive voice fails.
    ("The fee is paid by the holder.", 1, 1),
    # A sentence over 25 words fails.
    (" ".join(["word"] * 26) + ".", 1, 1),
    # Code, equation and header lines are not prose.
    ("Args:\n    m = 1 + a * T\n    |a|b|\nThe mint pays the wage.", 1, 0),
])
def test_sentences_are_split_and_judged(doc, n_sentences, n_failing):
    """Each case can fail: a wrong split changes the count, a wrong rule the faults."""
    found = sentences(doc)
    assert len(found) == n_sentences
    assert sum(bool(judge(s)) for s in found) == n_failing
