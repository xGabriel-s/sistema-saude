from flask import Blueprint, request, jsonify
from bson import ObjectId
from database.mongo import atendimentos
from services.fila_service import (
    gerar_posicao,
    calcular_previsao,
    finalizar_atendimento
)
from models.atendimento_model import criar_atendimento
from datetime import datetime

atendimento_bp = Blueprint("atendimento", __name__)

# Paciente entra na fila
@atendimento_bp.route("/fila/entrar", methods=["POST"])
def entrar_fila():
    data = request.json

    existente = atendimentos.find_one({
        "cpf": data["cpf"],
        "status": {"$in": ["AGUARDANDO", "EM_ATENDIMENTO"]}
    })

    if existente:
        return jsonify({"msg": "Paciente já está na fila"}), 400

    posicao = gerar_posicao(data["tipo_atendimento"])
    previsao = calcular_previsao(posicao)

    atendimento = criar_atendimento(data, posicao, previsao)
    atendimentos.insert_one(atendimento)

    return jsonify({
        "msg": "Entrada realizada",
        "posicao": posicao,
        "previsao": previsao
    })


# Atendente visualiza fila
@atendimento_bp.route("/fila", methods=["GET"])
def listar_fila():
    fila = list(atendimentos.find().sort("entrada", 1))
    for f in fila:
        f["_id"] = str(f["_id"])
    return jsonify(fila)


# Atendente chama paciente
@atendimento_bp.route("/chamar/<id>", methods=["PUT"])
def chamar(id):
    atendimentos.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"status": "EM_ATENDIMENTO", "inicio": datetime.now()}}
    )
    return jsonify({"msg": "Paciente em atendimento"})


# Atendente finaliza atendimento
@atendimento_bp.route("/finalizar/<id>", methods=["PUT"])
def finalizar(id):
    atendimento = atendimentos.find_one({"_id": ObjectId(id)})
    finalizar_atendimento(atendimento)
    atendimentos.delete_one({"_id": ObjectId(id)})
    return jsonify({"msg": "Atendimento finalizado"})


# Paciente consulta situação
@atendimento_bp.route("/consulta/<cpf>", methods=["GET"])
def consultar(cpf):
    atendimento = atendimentos.find_one({"cpf": cpf})

    if not atendimento:
        return jsonify({"msg": "Paciente não encontrado"}), 404

    return jsonify({
        "nome": atendimento["nome"],
        "status": atendimento["status"],
        "posicao": atendimento["posicao"],
        "previsao": atendimento["previsao_minutos"]
    })
