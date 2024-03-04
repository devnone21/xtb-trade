import pandas as pd
import pickle
from model import Model
from sklearn.model_selection import train_test_split

dataset_file = "dataset.csv"
model_file = "knn.pickle"

# Read csv file
df = pd.read_csv(dataset_file)

# Split DataFrame into X, Y
X = df.iloc[:, :-1].values.tolist()
Y = df.iloc[:, -1].values.tolist()

# Separate data for train and test
train_test_tuples = train_test_split(X, Y, test_size=0.2, random_state=42, stratify=Y)
model = Model(*train_test_tuples)


# train K-1 and show result
model.train_knn(k=1)
print(f'acc: {model.accuracy}, rpt: {model.report}')


# search best K
bestK = bestScore = 0
for n in range(1, 10):
    model.train_knn(k=n)
    if model.accuracy > bestScore:
        bestScore = model.accuracy
        bestK = n
print(f'bestK: {bestK}, bestAcc: {bestScore}')


# recalculate best result again and show result
ml = model.train_knn(k=bestK)
print(f'acc: {model.accuracy}, rpt: {model.report}')


# save model to pickle file
with open(model_file, "wb") as fn:
    pickle.dump(ml, fn)


# load model pickle file and use
with open(model_file, "rb") as fn:
    ml = pickle.load(fn)


# Test model
inputX = [[18, 0, 130, 19.5]]
outputY = ml.predict(inputX)
print(f'output: {outputY}')
