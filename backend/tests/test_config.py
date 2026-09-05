from ffedge import config


def test_my_picks_slot4():
    assert config.my_picks(4, 12, 12) == [4, 21, 28, 45, 52, 69, 76, 93, 100, 117, 124, 141]


def test_my_picks_slot5_15_rounds():
    assert config.my_picks(5, 12, 15) == [5, 20, 29, 44, 53, 68, 77, 92, 101, 116, 125, 140, 149, 164, 173]


def test_league_json_loaded():
    assert config.MY_SLOT == 5 and config.ROUNDS == 15 and config.BENCH_SLOTS == 6
    assert config.TEAM_NAMES[5] == "Show Me Your TDs" and config.MY_SCHEDULE[1] == "Injured Reserve"


def test_team_on_clock_snake():
    assert config.team_on_clock(1) == 1
    assert config.team_on_clock(5) == 5
    assert config.team_on_clock(12) == 12
    assert config.team_on_clock(13) == 12
    assert config.team_on_clock(20) == 5
    assert config.team_on_clock(29) == 5
    assert config.round_of(29) == 3
