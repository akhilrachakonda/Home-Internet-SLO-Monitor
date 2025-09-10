from sklearn.ensemble import IsolationForest

class SlidingIForest:
    def __init__(self, window=120, random_state=42):
        self.window = window
        self.X = []
        self.model = IsolationForest(contamination=0.05, random_state=random_state)
        self.ready = False
    def add(self, p95_s, jitter_ms, loss_pct, mbps):
        self.X.append([p95_s, jitter_ms, loss_pct, mbps])
        if len(self.X) > self.window:
            self.X = self.X[-self.window:]
        if len(self.X) > 30:
            self.model.fit(self.X)
            self.ready = True
            score = -self.model.decision_function([self.X[-1]])[0]  # higher = worse
        else:
            score = 0.0
        return score
