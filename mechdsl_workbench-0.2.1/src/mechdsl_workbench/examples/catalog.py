"""Metadata and source loading for bundled mechanics and algorithm examples."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib.resources import files
from typing import Any, Literal

ExampleMode = Literal["mechanics", "algorithm"]


@dataclass(frozen=True, slots=True)
class Example:
    id: str
    mode: ExampleMode
    title: str
    description: str
    difficulty: str
    tags: tuple[str, ...]
    source_file: str
    energy_file: str | None = None

    def metadata(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("source_file")
        data.pop("energy_file")
        data["has_energy_source"] = self.energy_file is not None
        return data


_EXAMPLES: tuple[Example, ...] = (
    Example(
        id="svk-hex8",
        mode="mechanics",
        title="SVK Hex8 cantilever",
        description="Canonical directive-driven first mechanics compile.",
        difficulty="first steps",
        tags=("SVK", "Hex8", "elasticity"),
        source_file="svk_hex8.tex",
    ),
    Example(
        id="equation-svk-hex8",
        mode="mechanics",
        title="Equation-bearing SVK Hex8",
        description="Adds field, constitutive-role, and weak-form declarations.",
        difficulty="intermediate",
        tags=("SVK", "Hex8", "equations"),
        source_file="equation_svk_hex8.tex",
    ),
    Example(
        id="svk-tet4",
        mode="mechanics",
        title="SVK Tet4",
        description="A compact element-type comparison source.",
        difficulty="first steps",
        tags=("SVK", "Tet4", "elasticity"),
        source_file="svk_tet4.tex",
    ),
    Example(
        id="algo-radial-return-j2",
        mode="algorithm",
        title="J2 radial return",
        description="Scalar Newton return map authored as algpseudocode.",
        difficulty="intermediate",
        tags=("algo2code", "J2", "plasticity"),
        source_file="radial_return_j2.tex",
    ),
    Example(
        id="algo-pcg",
        mode="algorithm",
        title="Preconditioned conjugate gradient",
        description="Canonical matrix-form PCG algorithm from the algo2code library.",
        difficulty="advanced",
        tags=("algo2code", "PCG", "solver"),
        source_file="pcg.tex",
    ),
)


def list_examples(*, mode: ExampleMode | None = None) -> list[dict[str, Any]]:
    examples = _EXAMPLES if mode is None else tuple(item for item in _EXAMPLES if item.mode == mode)
    return [example.metadata() for example in examples]


def get_example(example_id: str) -> dict[str, Any]:
    example = next((item for item in _EXAMPLES if item.id == example_id), None)
    if example is None:
        raise KeyError(example_id)

    data_root = files("mechdsl_workbench.examples").joinpath("data")
    source = data_root.joinpath(example.source_file).read_text(encoding="utf-8")
    energy_source = (
        data_root.joinpath(example.energy_file).read_text(encoding="utf-8")
        if example.energy_file
        else None
    )

    return {
        **example.metadata(),
        "source": source,
        "problem_source": source if example.mode == "mechanics" else None,
        "algorithm_source": source if example.mode == "algorithm" else None,
        "energy_source": energy_source,
    }
