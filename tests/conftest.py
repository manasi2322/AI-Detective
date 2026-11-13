from pathlib import Path

import pytest

from detective.loader import load_case, load_solution
from detective.pipeline import investigate

CASE1 = Path(__file__).resolve().parent.parent / "cases" / "case1_missing_laptop"


@pytest.fixture(scope="session")
def case1():
    return load_case(CASE1)


@pytest.fixture(scope="session")
def solution1():
    return load_solution(CASE1)


@pytest.fixture(scope="session")
def inv1(case1):
    return investigate(case1)
