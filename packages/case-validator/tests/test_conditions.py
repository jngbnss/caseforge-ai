from pydantic import TypeAdapter

from case_validator.conditions import ConditionState, evaluate, iter_atoms
from case_validator.schema import Condition

parse = TypeAdapter(Condition).validate_python

STATE = ConditionState(
    collected=frozenset({"ev-01", "ev-03"}),
    presented={"suspect-01": frozenset({"ev-01"})},
    solved=frozenset({"pz-01"}),
    trust={"suspect-01": 2, "suspect-02": 0},
)


def test_atoms():
    assert evaluate(parse({"always": True}), STATE)
    assert evaluate(parse({"evidence_collected": "ev-03"}), STATE)
    assert not evaluate(parse({"evidence_collected": "ev-04"}), STATE)
    assert evaluate(parse({"puzzle_solved": "pz-01"}), STATE)
    assert not evaluate(parse({"puzzle_solved": "pz-02"}), STATE)


def test_presented_and_trust_respect_npc():
    assert evaluate(parse({"evidence_presented": "ev-01", "npc": "suspect-01"}), STATE)
    assert not evaluate(parse({"evidence_presented": "ev-01", "npc": "suspect-02"}), STATE)
    assert evaluate(parse({"evidence_presented": "ev-01"}), STATE)  # any NPC
    assert evaluate(parse({"trust_gte": 2, "npc": "suspect-01"}), STATE)
    assert not evaluate(parse({"trust_gte": 1, "npc": "suspect-02"}), STATE)


def test_contextual_npc_is_used_when_atom_omits_it():
    cond = parse({"trust_gte": 1})
    assert evaluate(cond, STATE, npc="suspect-01")
    assert not evaluate(cond, STATE, npc="suspect-02")
    shown = parse({"evidence_presented": "ev-01"})
    assert not evaluate(shown, STATE, npc="suspect-02")


def test_all_any_and_empty_combinators():
    both = parse({"all": [{"evidence_collected": "ev-01"}, {"trust_gte": 2, "npc": "suspect-01"}]})
    either = parse({"any": [{"evidence_collected": "ev-99"}, {"puzzle_solved": "pz-01"}]})
    assert evaluate(both, STATE)
    assert evaluate(either, STATE)
    assert evaluate(parse({"all": []}), STATE)
    assert not evaluate(parse({"any": []}), STATE)


def test_iter_atoms_flattens_nested_conditions():
    cond = parse(
        {"all": [{"any": [{"puzzle_solved": "a"}, {"evidence_collected": "b"}]}, {"trust_gte": 1}]}
    )
    assert len(list(iter_atoms(cond))) == 3
    assert list(iter_atoms(None)) == []
