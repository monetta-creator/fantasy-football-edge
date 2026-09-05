from ffedge import rosters


def test_seed_add_drop_move(tmp_path):
    db = tmp_path / "r.db"
    picks = [{"pick_no": 1, "player_id": "RB:a", "team": 1}, {"pick_no": 5, "player_id": "WR:b", "team": 5}]
    assert rosters.seed_from_draft(picks, path=db) == 2
    assert rosters.owner_of(db) == {"RB:a": 1, "WR:b": 5}
    rosters.move(5, "WR:b", "WR", db)
    assert rosters.roster(5, db)[0]["slot"] == "WR"
    try:
        rosters.add(5, "RB:a", path=db); assert False
    except ValueError:
        pass
    rosters.drop(1, "RB:a", db)
    rosters.add(5, "RB:a", "BN", db)
    assert {r["player_id"] for r in rosters.roster(5, db)} == {"RB:a", "WR:b"}
    rosters.set_lineup(5, {"RB:a": "RB"}, db)
    slots = {r["player_id"]: r["slot"] for r in rosters.roster(5, db)}
    assert slots == {"RB:a": "RB", "WR:b": "BN"}
    rosters.replace_team(5, ["WR:b"], {"WR:b": "IR"}, db)
    assert rosters.roster(5, db) == [{"player_id": "WR:b", "slot": "IR"}]
