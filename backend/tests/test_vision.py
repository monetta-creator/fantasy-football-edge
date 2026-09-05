from ffedge.players import Player
from ffedge.vision import match_player, resolve


def _p(name, pos, team, adp=50.0):
    return Player(id=f"{pos}:{name.lower().replace(' ', '').replace('.', '').replace(chr(39), '')}", name=name, pos=pos, team=team, stats={}, pts=100, games=17, ppg=5.9,
                  adp=adp, adp_sigma=5, adp_sources={}, proj_sources={}, proj_spread=0, yahoo_rank=None, yahoo_id=None, espn_id=None,
                  sleeper_id=None, bye=6, injury={})


POOL = [_p("Jahmyr Gibbs", "RB", "DET", 1.4), _p("Bijan Robinson", "RB", "ATL", 2.2), _p("Brian Robinson", "RB", "SF", 80), _p("Jaxon Smith-Njigba", "WR", "SEA", 6.9), _p("Josh Allen", "QB", "BUF", 20),
        _p("Chase Brown", "RB", "CIN", 16), _p("Ja'Marr Chase", "WR", "CIN", 3.7), _p("A.J. Brown", "WR", "PHI", 22),
        _p("Derrick Henry", "RB", "BAL", 17), _p("HOU D/ST", "DEF", "HOU", 94)]


def test_abbreviated_names_match():
    assert match_player("J. Gibbs", POOL)[0][0].name == "Jahmyr Gibbs"
    assert match_player("Smith-Njigba", POOL)[0][0].name == "Jaxon Smith-Njigba"
    assert match_player("Ja'Marr Chase", POOL, "WR", "CIN")[0][0].name == "Ja'Marr Chase"


def test_position_disambiguates_brown():
    assert match_player("Brown", POOL, "RB")[0][0].name == "Chase Brown"
    assert match_player("A. Brown", POOL, "WR")[0][0].name == "A.J. Brown"


def test_defense_and_grid_pick_numbers():
    ex = {"board_type": "grid", "picks": [
        {"pick_no": None, "round": 2, "column": 4, "player": "Houston", "position": "DEF", "nfl_team": None, "fantasy_team": None},
        {"pick_no": None, "round": 1, "column": 1, "player": "J. Gibbs", "position": "RB", "nfl_team": "DET", "fantasy_team": "Bob"},
        {"pick_no": None, "round": 1, "column": 2, "player": "Zzyzx", "position": "WR", "nfl_team": None, "fantasy_team": None},
    ]}
    rows = resolve(ex, POOL, set(), {1: "Bob", 2: "Team 2"})
    by = {r["text"]: r for r in rows}
    assert by["J. Gibbs"]["player_name"] == "Jahmyr Gibbs" and by["J. Gibbs"]["pick_no"] == 1 and by["J. Gibbs"]["team"] == 1 and by["J. Gibbs"]["status"] == "ok"
    assert by["Houston"]["pick_no"] == 21 and by["Houston"]["player_name"] == "HOU D/ST"  # round 2, column 4 -> pick 21 in a snake
    assert by["Zzyzx"]["status"] == "unknown"
    assert [r["pick_no"] for r in rows] == [1, 2, 21]


def test_already_drafted_flag():
    ex = {"board_type": "list", "picks": [{"pick_no": 1, "round": 1, "column": None, "player": "Jahmyr Gibbs", "position": "RB", "nfl_team": "DET", "fantasy_team": None}]}
    rows = resolve(ex, POOL, {"RB:jahmyrgibbs"}, {})
    assert rows[0]["status"] == "already_drafted"


def test_team_hint_breaks_initial_last_name_tie():
    ex = {"board_type": "grid", "picks": [{"pick_no": 2, "round": 1, "column": 2, "player": "B. Robinson", "position": "RB", "nfl_team": "ATL", "fantasy_team": None}]}
    rows = resolve(ex, POOL, set(), {})
    assert rows[0]["player_name"] == "Bijan Robinson" and rows[0]["status"] == "ok"
    ex["picks"][0]["nfl_team"] = None
    assert resolve(ex, POOL, set(), {})[0]["status"] == "ambiguous"
