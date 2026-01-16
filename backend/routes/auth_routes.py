from flask import Blueprint, request, jsonify
from config import ADMIN_USER, ADMIN_PASSWORD

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json

    if (
        data["username"] == ADMIN_USER and
        data["password"] == ADMIN_PASSWORD
    ):
        return jsonify({"msg": "Login autorizado", "perfil": "ADMIN"})

    return jsonify({"msg": "Credenciais inválidas"}), 401
