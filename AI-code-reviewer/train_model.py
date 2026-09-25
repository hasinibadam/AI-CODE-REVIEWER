import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import pickle

data = {
    "code": [
        "print('hello')",
        "def add(a,b): return a+b",
        "for i in range(10): print(i)",
        "a=1",
        "def func(): pass"
    ],
    "label": [
        "bad",
        "good",
        "average",
        "bad",
        "average"
    ]
}

df = pd.DataFrame(data)

vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(df["code"])

model = LogisticRegression()
model.fit(X, df["label"])

pickle.dump(model, open("model.pkl", "wb"))
pickle.dump(vectorizer, open("vectorizer.pkl", "wb"))

print("Model ready!")