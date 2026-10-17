import pytest 
from src.costs import fill_cost

def test_fill_cost():
    assert fill_cost(10000, "regular") == pytest.approx(6.0)
    assert fill_cost(10000, "vip4") == pytest.approx(4.0)
    assert fill_cost(10000, "vip7") == pytest.approx(3.2)

def test_round_trip_regular():
    assert 4 * fill_cost(10000, "regular") == pytest.approx(24.0)