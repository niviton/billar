from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# Configurar Firebase
cred = credentials.Certificate("chave-firebase.json")  # Substitua pelo seu JSON real do Firebase
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route("/")
def home():
    return "Servidor Flask rodando no PythonAnywhere!"

@app.route("/fazer_pedido", methods=["POST"])
def fazer_pedido():
    data = request.json
    pedido_ref = db.collection("pedidos").add(data)
    return jsonify({"message": "Pedido adicionado!", "id": pedido_ref[1].id})

if __name__ == "__main__":
    app.run(debug=True)
