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

## Sample output

```text
Which team's scores do you want? Enter a team name or abbreviation: NE

New England Patriots scores from the past 7 days:
  Sun Nov 15, 2026 at 09:30 AM Eastern Standard Time - L, NE 10, Detroit Lions 35
  Sun Nov 08, 2026 at 04:25 PM Eastern Standard Time - L, NE 27, Green Bay Packers 45

Upcoming games:
  Sun Nov 29, 2026 at 08:20 PM Eastern Standard Time - NE at Los Angeles Chargers
  Sun Dec 06, 2026 at 04:25 PM Eastern Standard Time - NE vs. Buffalo Bills
  Thu Dec 10, 2026 at 08:15 PM Eastern Standard Time - NE vs. Minnesota Vikings
  Mon Dec 21, 2026 at 08:15 PM Eastern Standard Time - NE at Kansas City Chiefs
  Sun Dec 27, 2026 at 01:00 PM Eastern Standard Time - NE at New York Jets
  Sun Jan 03, 2027 at 12:00 AM Eastern Standard Time - NE vs. Denver Broncos
  Sun Jan 10, 2027 at 12:00 AM Eastern Standard Time - NE vs. Miami Dolphins

Broadcasts for the next 3 games:
  Sun Nov 29, 2026 at 08:20 PM Eastern Standard Time - Los Angeles Chargers: NBC
  Sun Dec 06, 2026 at 04:25 PM Eastern Standard Time - Buffalo Bills: CBS
  Thu Dec 10, 2026 at 08:15 PM Eastern Standard Time - Minnesota Vikings: Prime Video

Projected outcomes for the next 3 games:
Projection uses each team's season-to-date points scored and allowed per game.

  Sun Nov 29, 2026 at 08:20 PM Eastern Standard Time - Los Angeles Chargers
  Projected score: NE 24.7, LAC 19.7 - New England Patriots projected to win
  Sample: NE 10 games; LAC 8 games.

  Sun Dec 06, 2026 at 04:25 PM Eastern Standard Time - Buffalo Bills
  Projected score: NE 22.7, BUF 28.1 - Buffalo Bills projected to win
  Sample: NE 10 games; BUF 8 games.

  Thu Dec 10, 2026 at 08:15 PM Eastern Standard Time - Minnesota Vikings
  Projected score: NE 18.3, MIN 21.2 - Minnesota Vikings projected to win
  Sample: NE 10 games; MIN 8 games.
```

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
