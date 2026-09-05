from ffedge.llm import grounded

FACTS = {"player": "Puka Nacua (WR, LAR)", "projected points (league scoring)": 336.1, "VORP vs waiver replacement": 161.7,
         "consensus ADP": 4.9, "my next pick": 21, "P(gone by my next pick)": 0.98, "mechanism": "Full PPR: 115 catches = 115 pts alone"}


def test_grounded_accepts_numbers_from_facts():
    assert grounded("Puka Nacua projects 336 pts, 162 over waiver WR, and is gone by #21 in 98% of sims.", FACTS, ["Puka Nacua"])


def test_grounded_rejects_invented_number():
    assert not grounded("Puka Nacua had 1,486 yards last year and projects 336 pts.", FACTS, ["Puka Nacua"])


def test_grounded_rejects_foreign_player_and_length():
    assert not grounded("Take Puka Nacua over Cooper Kupp; 336 pts.", FACTS, ["Puka Nacua"])
    assert not grounded(" ".join(["word"] * 40), FACTS, ["Puka Nacua"])


def test_grounded_tolerates_verb_before_name_but_not_invented_player():
    assert grounded("Draft Puka Nacua: 336 pts.", FACTS, ["Puka Nacua"])
    assert not grounded("Draft Puka Nacua over Random Guy: 336 pts.", FACTS, ["Puka Nacua"])


def test_grounded_allows_sources_cities_and_percentiles():
    facts = {"my 10th-90th percentile": [8.0, 32.4], "win probability": 0.509, "team": "New England"}
    assert grounded("The Kalshi market and Vegas agree; New England sits at the 90th percentile, 50.9% to win.", facts, [])
