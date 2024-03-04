from typing import Union, Dict
from dataclasses import dataclass
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import classification_report
from sklearn.metrics import accuracy_score


@dataclass
class Model:
    X_train: list
    X_test: list
    Y_train: list
    Y_test: list
    report: Union[str, Dict] = ""
    accuracy: float = 0.0

    def train_knn(self, k: int):
        _knn = KNeighborsClassifier(n_neighbors=k)
        _knn.fit(self.X_train, self.Y_train)
        _answer = _knn.predict(self.X_test)
        self.report = classification_report(self.Y_test, _answer, zero_division=1)
        self.accuracy = accuracy_score(self.Y_test, _answer)
        return _knn
