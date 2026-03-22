"""Tests for astar/types.py — terrain constants and class mapping."""

from astar.types import (
    OCEAN, PLAINS, EMPTY, SETTLEMENT, PORT, RUIN, FOREST, MOUNTAIN,
    CLASS_EMPTY, CLASS_SETTLEMENT, CLASS_PORT, CLASS_RUIN, CLASS_FOREST, CLASS_MOUNTAIN,
    TERRAIN_TO_CLASS, NUM_CLASSES,
)


def test_terrain_to_class_ocean():
    assert TERRAIN_TO_CLASS[OCEAN] == CLASS_EMPTY


def test_terrain_to_class_plains():
    assert TERRAIN_TO_CLASS[PLAINS] == CLASS_EMPTY


def test_terrain_to_class_empty():
    assert TERRAIN_TO_CLASS[EMPTY] == CLASS_EMPTY


def test_terrain_to_class_settlement():
    assert TERRAIN_TO_CLASS[SETTLEMENT] == CLASS_SETTLEMENT


def test_terrain_to_class_port():
    assert TERRAIN_TO_CLASS[PORT] == CLASS_PORT


def test_terrain_to_class_ruin():
    assert TERRAIN_TO_CLASS[RUIN] == CLASS_RUIN


def test_terrain_to_class_forest():
    assert TERRAIN_TO_CLASS[FOREST] == CLASS_FOREST


def test_terrain_to_class_mountain():
    assert TERRAIN_TO_CLASS[MOUNTAIN] == CLASS_MOUNTAIN


def test_num_classes():
    assert NUM_CLASSES == 6


def test_all_terrain_codes_mapped():
    """Every terrain code we encounter should have a mapping."""
    for code in [OCEAN, PLAINS, EMPTY, SETTLEMENT, PORT, RUIN, FOREST, MOUNTAIN]:
        assert code in TERRAIN_TO_CLASS
