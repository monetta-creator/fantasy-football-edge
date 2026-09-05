from ffedge import config, draft_state


def test_pick_undo_reset(tmp_path):
    db = tmp_path / "t.db"
    assert draft_state.get_picks(db) == []
    r = draft_state.add_pick("RB:a", None, db)
    assert r["pick_no"] == 1 and r["team"] == 1
    r = draft_state.add_pick("RB:b", None, db)
    assert r["pick_no"] == 2 and r["team"] == 2
    try:
        draft_state.add_pick("RB:a", None, db)
        assert False
    except ValueError:
        pass
    u = draft_state.undo(db)
    assert u["player_id"] == "RB:b"
    assert len(draft_state.get_picks(db)) == 1
    draft_state.reset(db)
    assert draft_state.get_picks(db) == []


def test_team_names(tmp_path):
    db = tmp_path / "t.db"
    names = draft_state.get_team_names(db)
    assert names[config.MY_SLOT] == config.TEAM_NAMES.get(config.MY_SLOT, "Me")
    assert len(names) == config.NUM_TEAMS
    draft_state.set_team_names({1: "Bob"}, db)
    assert draft_state.get_team_names(db)[1] == "Bob"
