"""Show recent and upcoming NFL games for a team using ESPN's public API."""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
PAST_DAYS = 7
PROJECTION_GAME_COUNT = 3
REQUEST_TIMEOUT = 15


@dataclass(frozen=True)
class Team:
    """Identify an NFL team using ESPN's ID, display name, and abbreviation."""

    id: str
    name: str
    abbreviation: str


@dataclass(frozen=True)
class TeamStats:
    """Hold a team's average points scored and allowed over completed games."""

    points_for: float
    points_against: float
    games: int


def fetch_json(endpoint: str, params: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Fetch and decode a JSON response from ESPN."""
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    if params:
        url = f"{url}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "NFLTeamScores/1.0"})
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            data = json.load(response)
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not reach ESPN ({exc}). Check your internet connection.") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("ESPN returned an unreadable response.") from exc

    if not isinstance(data, dict):
        raise RuntimeError("ESPN returned an unexpected response format.")
    return data


def load_teams() -> list[Team]:
    """Fetch ESPN's active NFL teams and convert them to Team records."""
    response = fetch_json("teams", {"limit": "100"})
    try:
        entries = response["sports"][0]["leagues"][0]["teams"]
        teams = [
            Team(
                id=str(entry["team"]["id"]),
                name=str(entry["team"]["displayName"]),
                abbreviation=str(entry["team"]["abbreviation"]),
            )
            for entry in entries
            if entry["team"].get("isActive", True)
        ]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("ESPN's team list was not in the expected format.") from exc
    if not teams:
        raise RuntimeError("ESPN did not return any NFL teams.")
    return teams


def choose_team(teams: list[Team]) -> Team:
    """Prompt until the user enters a listed team's name or abbreviation."""
    print("Available teams: " + ", ".join(team.abbreviation for team in teams))
    while True:
        answer = input("Which team's scores do you want? Enter a team name or abbreviation: ")
        normalized = "".join(character for character in answer.casefold() if character.isalnum())
        matches = [
            team
            for team in teams
            if normalized
            in {
                "".join(character for character in value.casefold() if character.isalnum())
                for value in (team.name, team.abbreviation)
            }
        ]
        if len(matches) == 1:
            return matches[0]
        print("I couldn't match that team. Try one of the abbreviations listed above.")


def load_schedule(team: Team) -> list[dict[str, Any]]:
    """Fetch and return the ESPN schedule events for a team."""
    response = fetch_json(f"teams/{team.id}/schedule")
    events = response.get("events")
    if not isinstance(events, list):
        raise RuntimeError(f"ESPN did not return a schedule for the {team.name}.")
    return [event for event in events if isinstance(event, dict)]


def event_datetime(event: Mapping[str, Any]) -> datetime | None:
    """Parse an event's ISO date, returning None when it is missing or invalid."""
    value = event.get("date")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def event_competition(event: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the event's first competition, or an empty mapping if unavailable."""
    competitions = event.get("competitions")
    if isinstance(competitions, list) and competitions and isinstance(competitions[0], dict):
        return competitions[0]
    return {}


def game_sides(
    event: Mapping[str, Any], team_id: str
) -> tuple[Mapping[str, Any], Mapping[str, Any]] | None:
    """Return the selected team's and opponent's competitors for an event."""
    competitors = event_competition(event).get("competitors")
    if not isinstance(competitors, list):
        return None
    selected = next(
        (
            competitor
            for competitor in competitors
            if isinstance(competitor, dict)
            and str(competitor.get("team", {}).get("id", "")) == team_id
        ),
        None,
    )
    opponent = next(
        (competitor for competitor in competitors if isinstance(competitor, dict) and competitor is not selected),
        None,
    )
    if selected is None or opponent is None:
        return None
    return selected, opponent


def score_value(value: Any) -> float | None:
    """Convert ESPN's string or object score representation to a finite number."""
    if isinstance(value, dict):
        value = value.get("value", value.get("displayValue"))
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    return score if math.isfinite(score) else None


def is_completed(event: Mapping[str, Any]) -> bool:
    """Return whether ESPN marks an event as finished."""
    status = event_competition(event).get("status", {})
    if not isinstance(status, dict):
        return False
    status_type = status.get("type", {})
    if not isinstance(status_type, dict):
        return False
    return status_type.get("completed") is True or status_type.get("state") == "post"


def team_stats(
    schedule: list[dict[str, Any]], team_id: str, now: datetime
) -> TeamStats | None:
    """Calculate season-to-date points-for and points-against averages."""
    points_for: list[float] = []
    points_against: list[float] = []
    for event in schedule:
        played_at = event_datetime(event)
        sides = game_sides(event, team_id)
        if played_at is None or played_at > now or not is_completed(event) or sides is None:
            continue
        own_score = score_value(sides[0].get("score"))
        opponent_score = score_value(sides[1].get("score"))
        if own_score is not None and opponent_score is not None:
            points_for.append(own_score)
            points_against.append(opponent_score)

    if not points_for:
        return None
    return TeamStats(
        points_for=sum(points_for) / len(points_for),
        points_against=sum(points_against) / len(points_against),
        games=len(points_for),
    )


def projected_points(own_stats: TeamStats, opponent_stats: TeamStats) -> tuple[float, float]:
    """Estimate both scores by averaging offense with the opponent's points allowed."""
    own_projection = (own_stats.points_for + opponent_stats.points_against) / 2
    opponent_projection = (opponent_stats.points_for + own_stats.points_against) / 2
    return own_projection, opponent_projection


def upcoming_games(
    schedule: list[dict[str, Any]], team_id: str, now: datetime
) -> list[dict[str, Any]]:
    """Return this team's future, uncompleted schedule events in date order."""
    events = [
        event
        for event in schedule
        if (played_at := event_datetime(event)) is not None
        and played_at > now
        and not is_completed(event)
        and game_sides(event, team_id) is not None
    ]
    return sorted(events, key=lambda event: event_datetime(event) or now)


def _display_name(competitor: Mapping[str, Any]) -> str:
    """Get a competitor's display name, abbreviation, or a safe fallback."""
    team = competitor.get("team", {})
    if isinstance(team, dict):
        return str(team.get("displayName") or team.get("abbreviation") or "Unknown team")
    return "Unknown team"


def _local_time(event: Mapping[str, Any]) -> str:
    """Format an event date in the computer's local time zone."""
    played_at = event_datetime(event)
    if played_at is None:
        return "Date and time TBD"
    return played_at.astimezone().strftime("%a %b %d, %Y at %I:%M %p %Z")


def _team_is_home(competitor: Mapping[str, Any]) -> bool:
    """Return whether ESPN lists this competitor as the home team."""
    return competitor.get("homeAway") == "home"


def _broadcast_names(summary: Mapping[str, Any]) -> str:
    """Extract unique network names from an ESPN event summary."""
    header = summary.get("header", {})
    competitions = header.get("competitions", []) if isinstance(header, dict) else []
    if not isinstance(competitions, list) or not competitions or not isinstance(competitions[0], dict):
        return "TBD (not listed by ESPN)"

    competition = competitions[0]
    names: list[str] = []
    direct = competition.get("broadcast")
    if isinstance(direct, str) and direct.strip():
        names.append(direct.strip())
    broadcasts = competition.get("broadcasts")
    if isinstance(broadcasts, list):
        for broadcast in broadcasts:
            if not isinstance(broadcast, dict):
                continue
            broadcast_names = broadcast.get("names", [])
            if isinstance(broadcast_names, list):
                names.extend(str(name).strip() for name in broadcast_names if str(name).strip())
            media = broadcast.get("media", {})
            if isinstance(media, dict):
                short_name = media.get("shortName")
                if isinstance(short_name, str) and short_name.strip():
                    names.append(short_name.strip())
    geo_broadcasts = competition.get("geoBroadcasts")
    if isinstance(geo_broadcasts, list):
        for broadcast in geo_broadcasts:
            if isinstance(broadcast, dict):
                media = broadcast.get("media", {})
                if isinstance(media, dict):
                    short_name = media.get("shortName")
                    if isinstance(short_name, str) and short_name.strip():
                        names.append(short_name.strip())

    unique_names = list(dict.fromkeys(names))
    return ", ".join(unique_names) if unique_names else "TBD (not announced)"


def game_broadcast(event: Mapping[str, Any]) -> str:
    """Fetch an event summary and return its listed TV broadcast, if available."""
    event_id = event.get("id")
    if not event_id:
        return "TBD (not listed by ESPN)"
    summary = fetch_json("summary", {"event": str(event_id)})
    return _broadcast_names(summary)


def print_recent_scores(schedule: list[dict[str, Any]], team: Team, now: datetime) -> None:
    """Print the team's completed games from the previous seven days."""
    start = now - timedelta(days=PAST_DAYS)
    recent = [
        event
        for event in schedule
        if (played_at := event_datetime(event)) is not None
        and start <= played_at <= now
        and is_completed(event)
    ]
    recent.sort(key=lambda event: event_datetime(event) or now, reverse=True)

    print(f"\n{team.name} scores from the past {PAST_DAYS} days:")
    if not recent:
        print("  No completed games in this period.")
        return
    for event in recent:
        sides = game_sides(event, team.id)
        if sides is None:
            continue
        own_score = score_value(sides[0].get("score"))
        opponent_score = score_value(sides[1].get("score"))
        if own_score is None or opponent_score is None:
            continue
        result = "W" if own_score > opponent_score else "L" if own_score < opponent_score else "T"
        print(
            f"  {_local_time(event)} - {result}, {team.abbreviation} {own_score:g}, "
            f"{_display_name(sides[1])} {opponent_score:g}"
        )


def print_upcoming(
    games: list[dict[str, Any]],
    team: Team,
    projection_data: dict[str, TeamStats | None],
    broadcasts: dict[str, str],
    projection_games: list[dict[str, Any]],
) -> None:
    """Print the full schedule, next broadcasts, and available score projections."""
    print("\nUpcoming games:")
    if not games:
        print("  No upcoming games are listed by ESPN.")
        return
    for event in games:
        sides = game_sides(event, team.id)
        if sides is None:
            continue
        opponent = sides[1]
        venue = "vs." if _team_is_home(sides[0]) else "at"
        print(f"  {_local_time(event)} - {team.abbreviation} {venue} {_display_name(opponent)}")

    print("\nBroadcasts for the next 3 games:")
    for event in games[:PROJECTION_GAME_COUNT]:
        sides = game_sides(event, team.id)
        if sides is None:
            continue
        print(
            f"  {_local_time(event)} - {_display_name(sides[1])}: "
            f"{broadcasts.get(str(event.get('id', '')), 'TBD (not listed by ESPN)')}"
        )

    print("\nProjected outcomes for the next 3 games:")
    print("Projection uses each team's season-to-date points scored and allowed per game.")
    if not projection_games:
        print("  No upcoming games are listed by ESPN.")
    for event in projection_games:
        sides = game_sides(event, team.id)
        if sides is None:
            continue
        opponent = sides[1]
        opponent_id = str(opponent.get("team", {}).get("id", ""))
        own_stats = projection_data.get(team.id)
        opponent_stats = projection_data.get(opponent_id)
        print(f"\n  {_local_time(event)} - {_display_name(opponent)}")
        if own_stats is None or opponent_stats is None:
            print("  Projection unavailable: not enough completed game scores for both teams.")
            continue

        own_projection, opponent_projection = projected_points(own_stats, opponent_stats)
        if own_projection > opponent_projection:
            outcome = f"{team.name} projected to win"
        elif own_projection < opponent_projection:
            outcome = f"{_display_name(opponent)} projected to win"
        else:
            outcome = "Projected tie"
        print(
            f"  Projected score: {team.abbreviation} {own_projection:.1f}, "
            f"{opponent.get('team', {}).get('abbreviation', _display_name(opponent))} "
            f"{opponent_projection:.1f} - {outcome}"
        )
        print(
            f"  Sample: {team.abbreviation} {own_stats.games} games; "
            f"{opponent.get('team', {}).get('abbreviation', 'Opponent')} "
            f"{opponent_stats.games} games."
        )


def run() -> None:
    """Load the selected team's ESPN data and display its scores and forecasts."""
    teams = load_teams()
    team = choose_team(teams)
    schedule = load_schedule(team)
    now = datetime.now(timezone.utc)

    print_recent_scores(schedule, team, now)
    games = upcoming_games(schedule, team.id, now)
    projection_games = games[:PROJECTION_GAME_COUNT]
    stats_by_team: dict[str, TeamStats | None] = {team.id: team_stats(schedule, team.id, now)}
    for event in projection_games:
        sides = game_sides(event, team.id)
        if sides is None:
            continue
        opponent_id = str(sides[1].get("team", {}).get("id", ""))
        if opponent_id and opponent_id not in stats_by_team:
            opponent = Team(
                id=opponent_id,
                name=_display_name(sides[1]),
                abbreviation=str(sides[1].get("team", {}).get("abbreviation", "")),
            )
            stats_by_team[opponent_id] = team_stats(load_schedule(opponent), opponent_id, now)
    broadcasts = {
        str(event.get("id", "")): game_broadcast(event)
        for event in games[:PROJECTION_GAME_COUNT]
    }
    print_upcoming(games, team, stats_by_team, broadcasts, projection_games)


if __name__ == "__main__":
    try:
        run()
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")