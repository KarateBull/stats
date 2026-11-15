# NFL Team Scores

A command-line app that asks for an NFL team and uses ESPN's public scoreboard
API to show its completed games from the past seven days, upcoming schedule,
simple score projections for its next three games, and TV broadcasts for those
games.

## Run

Requires Python 3.10 or newer. No third-party packages are needed.

```powershell
python stats.py
```

Enter an NFL team abbreviation (such as `KC`) or its full team name.

## Projection notes

The projection is a basic estimate, not an ESPN prediction or betting line. For
each team, it averages its season-to-date points scored per game with its
opponent's points allowed per game; the opposing score is calculated the same
way. Early-season estimates use a small sample. The estimate does not account
for injuries, player availability, weather, or other matchup factors. ESPN may
not have announced a future game's broadcast yet; in that case the app reports
that it is TBD.

The app uses ESPN's publicly accessible, undocumented endpoints and requires
an internet connection. Those endpoints and response formats may change.
