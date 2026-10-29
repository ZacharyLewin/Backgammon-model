"""
Tests for the rules. Run with:  python -m pytest -q
Each test is a rule of backgammon written as code — a good way to read the engine.
"""
import random

from bgmodel.board import BAR, OFF, Board, legal_plays, result_type
from bgmodel.game import play_game
from bgmodel.strategies import STRATEGIES


def test_starting_pip_count_is_167():
    b = Board.start()
    assert b.pips() == 167 and b.opp_pips() == 167
    assert sum(b.me) == 15 and sum(b.opp) == 15


def test_opening_31_can_make_the_5_point():
    plays = legal_plays(Board.start(), (3, 1))
    assert any(p.after.me[5] == 2 for p in plays)


def test_doubles_play_four_times():
    plays = legal_plays(Board.start(), (6, 6))
    assert all(len(p.steps) == 4 for p in plays)


def test_dancing_on_a_closed_board():
    # I'm on the bar; opponent holds all six of their home points.
    b = Board.from_points({BAR: 1, 6: 14}, {1: 2, 2: 2, 3: 2, 4: 2, 5: 2, 6: 2})
    plays = legal_plays(b, (6, 5))
    assert len(plays) == 1 and plays[0].steps == ()


def test_must_play_the_larger_die_when_only_one_can_be_played():
    # One checker on 13. 3 then 5 (or 5 then 3) both land on 5, which is blocked.
    b = Board.from_points({13: 1}, {20: 2})   # opp point 20 = my point 5
    plays = legal_plays(b, (3, 5))
    assert [p.notation() for p in plays] == ["13/8"]


def test_bearing_off_with_a_higher_die():
    b = Board.from_points({2: 1, 1: 1}, {24: 15})
    plays = legal_plays(b, (6, 5))
    assert any(p.after.me[OFF] == 15 for p in plays)


def test_cannot_bear_off_with_higher_die_while_a_higher_checker_remains():
    b = Board.from_points({5: 1, 2: 1}, {24: 15})
    for p in legal_plays(b, (4, 1)):
        # the 4 must move 5/1, it cannot bear the 2 off
        assert p.after.me[2] in (0, 1)
        assert ("2/off" not in p.notation()) or ("5/1" in p.notation())


def test_hit_sends_checker_to_bar():
    b = Board.from_points({13: 1}, {24: 14, 15: 1})   # opp point 15 = my point 10
    plays = legal_plays(b, (3, 1))
    hit = [p for p in plays if p.hits]
    assert hit and all(p.after.opp[BAR] == 1 for p in hit)


def test_gammon_and_backgammon_classification():
    winner = Board.from_points({}, {}).me            # all off
    assert result_type(winner, Board.from_points({1: 15}, {}).me) == ("gammon", 2)
    assert result_type(winner, Board.from_points({20: 1, 1: 14}, {}).me) == ("backgammon", 3)
    assert result_type(winner, Board.from_points({1: 1}, {}).me) == ("single", 1)


def test_random_games_never_break_the_rules():
    rng = random.Random(7)
    s = STRATEGIES["random"]
    for _ in range(50):
        g = play_game(s, s, rng)
        for t in g.turns:
            b = Board.from_position_id(t.position_id)
            assert sum(b.me) == 15 and sum(b.opp) == 15
            for p in range(1, 25):
                assert not (b.me[p] and b.opp[25 - p]), "two colours on one point"
        assert g.points in (1, 2, 3)
