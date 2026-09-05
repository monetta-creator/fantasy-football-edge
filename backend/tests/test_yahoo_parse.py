from ffedge.sync import yahoo

ROSTER_JSON = {"fantasy_content": {"league": [{"league_key": "470.l.872372"}, {"teams": {"0": {"team": [
    [{"team_key": "470.l.872372.t.5"}, {"team_id": "5"}, {"name": "Show Me Your TDs"}],
    {"roster": {"0": {"players": {"0": {"player": [
        [{"player_key": "470.p.1"}, {"player_id": "1"}, {"name": {"full": "Puka Nacua"}}, {"editorial_team_abbr": "LAR"}, {"display_position": "WR"}, {"status": "Q"}],
        {"selected_position": [{"position": "WR"}]},
    ]}, "count": 1}}}},
]}, "count": 1}}]}}

TX_JSON = {"fantasy_content": {"league": [{}, {"transactions": {"0": {"transaction": [
    {"transaction_id": "12", "type": "add/drop", "status": "successful", "timestamp": "1700000000"},
    {"players": {"0": {"player": [
        [{"player_id": "9"}, {"name": {"full": "Breece Hall"}}, {"editorial_team_abbr": "NYJ"}, {"display_position": "RB"}],
        {"transaction_data": [{"type": "add", "source_type": "freeagents", "destination_team_key": "470.l.872372.t.5"}]},
    ]}, "count": 1}},
]}, "count": 1}}]}}


def test_parse_rosters():
    teams = yahoo.parse_rosters(ROSTER_JSON)
    assert teams[0]["team_id"] == 5 and teams[0]["name"] == "Show Me Your TDs"
    p = teams[0]["players"][0]
    assert p["name"] == "Puka Nacua" and p["pos"] == "WR" and p["team"] == "LAR" and p["slot"] == "WR" and p["status"] == "Q"


def test_parse_transactions():
    tx = yahoo.parse_transactions(TX_JSON)
    assert tx[0]["type"] == "add/drop" and tx[0]["players"][0]["type"] == "add"
    assert tx[0]["players"][0]["destination_team_key"].endswith(".t.5")


def test_auth_url_and_league_key_shape():
    c = yahoo.YahooClient("id", "secret", token_path=__import__("pathlib").Path("/nonexistent/x.json"))
    assert "client_id=id" in c.auth_url() and "redirect_uri=oob" in c.auth_url()
    assert not c.connected()
