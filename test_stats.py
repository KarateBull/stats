"""Run from the project folder with `python -m unittest -v` (or `py -m unittest -v`)."""

import unittest
from datetime import datetime, timezone

from stats import (
    Team,
    TeamStats,
    _broadcast_names,
    projected_points,
    score_value,
    team_stats,
    upcoming_games,
)


class StatsTests(unittest.TestCase):
    def test_score_value_handles_both_score_formats(self) -> None:
        self.assertEqual(score_value("24"), 24.0)
        self.assertEqual(score_value({"value": 17, "displayValue": "17"}), 17.0)
        self.assertIsNone(score_value(""))

    def test_team_stats_only_uses_completed_games_before_now(self) -> None:
        team = Team(id="1", name="Team One", abbreviation="ONE")
        schedule = [
            {
                "date": "2026-11-10T18:00:00Z",
                "competitions": [
                    {
                        "status": {"type": {"state": "post", "completed": True}},
                        "competitors": [
                            {"team": {"id": "1"}, "score": {"value": 28}},
                            {"team": {"id": "2"}, "score": {"value": 14}},
                        ],
                    }
                ],
            },
            {
                "date": "2026-11-12T18:00:00Z",
                "competitions": [
                    {
                        "status": {"type": {"state": "in", "completed": False}},
                        "competitors": [
                            {"team": {"id": "1"}, "score": "7"},
                            {"team": {"id": "2"}, "score": "0"},
                        ],
                    }
                ],
            },
        ]

        result = team_stats(schedule, team.id, datetime(2026, 11, 15, tzinfo=timezone.utc))

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.games, 1)
        self.assertEqual(result.points_for, 28)
        self.assertEqual(result.points_against, 14)

    def test_upcoming_games_excludes_completed_and_past_events(self) -> None:
        now = datetime(2026, 11, 15, tzinfo=timezone.utc)
        schedule = []
        for event_id, date, state, completed in (
            ("past", "2026-11-10T18:00:00Z", "post", True),
            ("future", "2026-11-20T18:00:00Z", "pre", False),
            ("completed", "2026-11-21T18:00:00Z", "post", True),
        ):
            schedule.append(
                {
                    "id": event_id,
                    "date": date,
                    "competitions": [
                        {
                            "status": {"type": {"state": state, "completed": completed}},
                            "competitors": [
                                {"team": {"id": "1"}, "homeAway": "home"},
                                {"team": {"id": "2"}, "homeAway": "away"},
                            ],
                        }
                    ],
                }
            )

        result = upcoming_games(schedule, "1", now)

        self.assertEqual([event["id"] for event in result], ["future"])

    def test_projected_points_average_offense_with_opponent_defense(self) -> None:
        team_score, opponent_score = projected_points(
            TeamStats(points_for=25, points_against=20, games=8),
            TeamStats(points_for=22, points_against=18, games=9),
        )

        self.assertEqual((team_score, opponent_score), (21.5, 21.0))

    def test_broadcast_names_are_deduplicated(self) -> None:
        summary = {
            "header": {
                "competitions": [
                    {
                        "broadcasts": [
                            {"media": {"shortName": "CBS"}, "names": ["CBS"]}
                        ],
                        "geoBroadcasts": None,
                    }
                ]
            }
        }
        self.assertEqual(_broadcast_names(summary), "CBS")

    def test_broadcast_names_handles_unannounced_broadcasts(self) -> None:
        summary = {"header": {"competitions": [{"broadcasts": None, "geoBroadcasts": None}]}}
        self.assertEqual(_broadcast_names(summary), "TBD (not announced)")


if __name__ == "__main__":
    unittest.main()
