from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/api/generer", methods=["POST"])
def generer():
    data = request.get_json()
    return jsonify({"message": "Backend opérationnel ✅", "input": data})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})
