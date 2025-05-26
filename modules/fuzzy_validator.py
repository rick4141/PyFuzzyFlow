import numpy as np
import skfuzzy as fuzz

class FuzzyValidator:
    def __init__(
        self,
        metric_func,
        thresholds,
        min_thresholds,
        history_size,
        update_every,
        label_names,
        mode="classic"
    ):
        """
        Initialize the FuzzyValidator.

        :param metric_func: Function that returns the metric value to classify.
        :param thresholds: List/array with main thresholds (will be updated dynamically).
        :param min_thresholds: Minimum thresholds (lower bound for dynamic updates).
        :param history_size: Number of samples to keep for threshold updates.
        :param update_every: How often to update thresholds, in number of samples.
        :param label_names: List of string labels, e.g. ["LOW", "MED", "HIGH"].
        :param mode: "classic" for rule-based fuzzy, "neuro-fuzzy" for neuro-fuzzy (experimental).
        """
        self.mode = mode
        self.metric_func = metric_func
        self.thresholds = np.array(thresholds)
        self.min_thresholds = np.array(min_thresholds)
        self.history_size = history_size
        self.update_every = update_every
        self.label_names = label_names
        self.history = []
        self.iter = 0

        if self.mode == "neuro-fuzzy":
            # Placeholder for future neuro-fuzzy model (e.g. ANFIS)
            # You could load or initialize your neural model here
            self.nf_model = None

    def update_thresholds(self):
        """
        Dynamically update thresholds using percentiles of the history.
        """
        percentiles = np.percentile(self.history, [30, 60, 85])
        self.thresholds = np.maximum(percentiles, self.min_thresholds)

    def classify(self, value):
        """
        Classic fuzzy logic membership using trapezoidal functions.
        """
        low, med, high = np.sort(self.thresholds)
        arr = np.array([value])
        # Trapezoidal membership parameters for each class
        a1, b1 = 0, 0
        c1, d1 = low * 0.8, low
        a2, b2 = low * 0.8, low
        c2, d2 = med, high * 0.8
        a3, b3 = med, high * 0.8
        c3, d3 = 100, 100
        low_pts = sorted([a1, b1, c1, d1])
        med_pts = sorted([a2, b2, c2, d2])
        high_pts = sorted([a3, b3, c3, d3])
        # Membership degrees
        low_val = fuzz.trapmf(arr, low_pts)[0]
        med_val = fuzz.trapmf(arr, med_pts)[0]
        high_val = fuzz.trapmf(arr, high_pts)[0]
        vals = [low_val, med_val, high_val]
        idx = np.argmax(vals)
        return self.label_names[idx], vals

    def classify_neuro_fuzzy(self, value):
        """
        Neuro-fuzzy membership.
        Here, as a placeholder, output is randomized to simulate a neural network softmax output.
        Replace with real neuro-fuzzy model inference when available.
        """
        import numpy as np
        vals = np.random.dirichlet(np.ones(len(self.label_names)), size=1)[0]
        idx = np.argmax(vals)
        return self.label_names[idx], vals

    def validate(self):
        """
        Evaluate the current metric value, update thresholds if needed,
        and classify using the selected mode.
        Returns: (value, label, membership_values)
        """
        value = self.metric_func()
        self.history.append(value)
        if len(self.history) > self.history_size:
            self.history.pop(0)
        self.iter += 1
        if self.iter % self.update_every == 0 and len(self.history) >= self.update_every:
            self.update_thresholds()

        if self.mode == "classic":
            label, vals = self.classify(value)
        elif self.mode == "neuro-fuzzy":
            print("[INFO] Neuro-fuzzy inference (experimental, random output)")
            label, vals = self.classify_neuro_fuzzy(value)
        else:
            raise ValueError(f"Unknown fuzzy mode: {self.mode}")

        return value, label, vals
