from app.anomaly import SlidingIForest

def test_iforest_learns():
    m = SlidingIForest(window=10)
    for _ in range(40):
        s = m.add(0.02, 2, 0.0, 100)
    assert m.ready is True
