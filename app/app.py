"""
Roman Urdu Scam / Fraud SMS Detector — Flask Backend
Partner B — Model + Custom HTML/CSS/JS UI (supports 3 models)

HOW TO RUN:
    1. Place this whole `app` folder (app.py, templates/, static/) inside
       your project as: roman-urdu-scam-detector/app/
    2. Make sure these exist in outputs/:
           nb_model.pkl, svm_model.pkl, lr_model.pkl, my_vectorizer.pkl
       (generated from the notebook — models you haven't saved yet will
       simply show as disabled in the UI)
    3. Install Flask once:
           pip install flask
    4. From the PROJECT ROOT folder, run:
           python app/app.py
    5. Open the link shown in the terminal (usually http://127.0.0.1:5000)
"""

from flask import Flask, render_template, request, jsonify
import pickle
import os
import re

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

MODEL_FILES = {
    "nb": ("nb_model.pkl", "Naive Bayes"),
    "svm": ("svm_model.pkl", "SVM"),
    "lr": ("lr_model.pkl", "Logistic Regression"),
}

models = {}
vectorizer = None
load_error = None

try:
    with open(os.path.join(OUTPUTS_DIR, "my_vectorizer.pkl"), "rb") as f:
        vectorizer = pickle.load(f)

    for key, (filename, _) in MODEL_FILES.items():
        path = os.path.join(OUTPUTS_DIR, filename)
        if os.path.exists(path):
            with open(path, "rb") as f:
                models[key] = pickle.load(f)
except Exception as e:
    load_error = str(e)


def basic_clean(text: str) -> str:
    text = text.lower()
    text = re.sub(r"http\S+|www\.\S+", " urltoken ", text)
    text = re.sub(r"\b\d{10,}\b", " phonetoken ", text)
    text = re.sub(r"\*\d+#", " shortcodetoken ", text)
    text = re.sub(r"\b\d+\b", " numtoken ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@app.route("/")
def home():
    return render_template("index.html", available_keys=list(models.keys()))


@app.route("/predict", methods=["POST"])
def predict():
    if load_error:
        return jsonify({"error": f"Model load failed: {load_error}"}), 500

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    model_key = data.get("model", "nb")

    if not message:
        return jsonify({"error": "Message khaali hai."}), 400

    if model_key not in models:
        return jsonify({"error": f"'{MODEL_FILES.get(model_key, (None, model_key))[1]}' abhi trained/saved nahi hai."}), 400

    model = models[model_key]
    cleaned = basic_clean(message)
    vector = vectorizer.transform([cleaned])
    prediction = model.predict(vector)[0]

    try:
        proba = model.predict_proba(vector)[0]
        confidence = round(max(proba) * 100, 1)
    except Exception:
        confidence = None

    return jsonify({
        "label": prediction,
        "confidence": confidence,
        "cleaned": cleaned,
        "model_used": MODEL_FILES[model_key][1],
    })


if __name__ == "__main__":
    app.run(debug=True)