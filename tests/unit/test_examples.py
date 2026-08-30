from __future__ import annotations

import pytest

from mechdsl_workbench.examples import get_example, list_examples

pytestmark = pytest.mark.unit


def test_example_ids_are_unique_and_cover_both_modes() -> None:
    examples = list_examples()
    ids = [example["id"] for example in examples]
    assert len(ids) == len(set(ids))
    assert {example["mode"] for example in examples} == {"mechanics", "algorithm"}


def test_mechanics_example_source_is_loaded_from_package_data() -> None:
    example = get_example("svk-hex8")
    assert example["mode"] == "mechanics"
    assert "% mechanics cell hex8" in example["source"]
    assert example["problem_source"] == example["source"]
    assert example["algorithm_source"] is None


def test_algorithm_example_source_is_loaded_from_package_data() -> None:
    example = get_example("algo-pcg")
    assert example["mode"] == "algorithm"
    assert "% algorithm pcg" in example["source"]
    assert "\\begin{algorithmic}" in example["algorithm_source"]
    assert example["problem_source"] is None


def test_examples_can_be_filtered_by_mode() -> None:
    algorithms = list_examples(mode="algorithm")
    assert algorithms
    assert all(example["mode"] == "algorithm" for example in algorithms)


def test_unknown_example_raises_key_error() -> None:
    with pytest.raises(KeyError):
        get_example("does-not-exist")
