"""Pytest entry point for Tenhou replay tests.

Parametrizes over all XML files in tests/xml/2024/ and replays
each round, verifying engine consistency with Tenhou's results.
"""

import glob
import os

import pytest

from . import driver, parser

XML_DIR = os.path.join(os.path.dirname(__file__), "..", "xml", "failed")
XML_FILES = sorted(glob.glob(os.path.join(XML_DIR, "*.xml")))


@pytest.mark.parametrize(
    "xml_path",
    XML_FILES,
    ids=[os.path.basename(p) for p in XML_FILES],
)
def test_replay(xml_path):
    """Replay all rounds in a Tenhou XML and verify engine consistency."""
    rounds = parser.parse(xml_path)
    for i, round_data in enumerate(rounds):
        driver.replay_round(round_data, round_index=i)
