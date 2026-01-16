from flask import Flask, request, jsonify
from flask_cors import CORS
from bson import ObjectId
from datetime import datetime, timedelta
import re
import jwt
from functools import wraps

# IMPORTANTE: seu database.mongo precisa exportar "users"
from database.mongo import pacientes, historico, counters, users

app = Flask(__name__)

# CORS (aceita OPTIONS automaticamente e libera chamadas do front)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

JWT_SECRET = "SEGREDO_SUPER_SEGURO"  # depois coloque em .env


# =========================================================
# AUTH (JWT)
# =========================================================
def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization")

        if not auth or not auth.startswith("Bearer "):
            return jsonify({"error": "Token ausente"}), 401

        token = auth.split(" ")[1]

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except Exception:
            return jsonify({"error": "Token inválido"}), 401

        return f(*args, **kwargs)
    return decorated


@app.route("/api/auth/login", methods=["POST"])
def login_atendente():
    dados = request.json or {}

    username = dados.get("username")
    password = dados.get("password")

    if not username or not password:
        return jsonify({"error": "Usuário e senha obrigatórios"}), 400

    user = users.find_one({"username": username, "active": True})
    if not user:
        return jsonify({"error": "Usuário inválido"}), 401

    # ✅ validação simples (senha em texto no Mongo)
    if user.get("password") != password:
        return jsonify({"error": "Senha inválida"}), 401

    token = jwt.encode(
        {
            "userId": str(user["_id"]),
            "role": user.get("role", "ATENDENTE"),
            "exp": datetime.utcnow().timestamp() + (60 * 60 * 8)  # 8h
        },
        JWT_SECRET,
        algorithm="HS256"
    )

    return jsonify({"token": token}), 200


# =========================================================
# UTILIDADES
# =========================================================
def somente_numeros(valor):
    return re.sub(r"\D", "", valor or "")


def serializar(doc):
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    for k, v in list(doc.items()):
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


def inicio_fim_dia(dt=None):
    dt = dt or datetime.now()
    inicio = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    fim = inicio + timedelta(days=1)
    return inicio, fim


def gerar_senha(tipo):
    hoje = datetime.now().strftime("%Y-%m-%d")
    chave = f"senha:{tipo}:{hoje}"

    resultado = counters.find_one_and_update(
        {"_id": chave},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )

    prefixo = "P" if tipo == "PREFERENCIAL" else "N"
    return f"{prefixo}-{str(resultado['seq']).zfill(3)}"


# =========================================================
# REGRA PREFERENCIAL: 1 preferencial a cada 2 normais
# =========================================================
def chave_normal_seq():
    hoje = datetime.now().strftime("%Y-%m-%d")
    return f"regra:normalSeq:{hoje}"


def get_normal_seq():
    doc = counters.find_one({"_id": chave_normal_seq()}) or {}
    return int(doc.get("seq", 0))


def inc_normal_seq():
    counters.update_one(
        {"_id": chave_normal_seq()},
        {"$inc": {"seq": 1}},
        upsert=True
    )


def reset_normal_seq():
    counters.update_one(
        {"_id": chave_normal_seq()},
        {"$set": {"seq": 0}},
        upsert=True
    )


# =========================================================
# ROTAS BÁSICAS
# =========================================================
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"ok": True})


# =========================================================
# ATENDENTE (PROTEGIDO)
# =========================================================
@app.route("/api/pacientes", methods=["POST"])
@auth_required
def cadastrar_paciente():
    dados = request.json or {}

    cpf_limpo = somente_numeros(dados.get("cpf"))
    tel_limpo = somente_numeros(dados.get("telefone"))

    if len(cpf_limpo) != 11:
        return jsonify({"error": "CPF inválido. Informe 11 dígitos."}), 400

    if not dados.get("nome") or not dados.get("tipo") or not dados.get("idade"):
        return jsonify({"error": "Campos obrigatórios ausentes."}), 400

    senha = gerar_senha(dados["tipo"])

    paciente = {
        "nome": dados["nome"],
        "cpf": cpf_limpo,
        "telefone": tel_limpo,
        "idade": int(dados["idade"]),
        "tipo": dados["tipo"],              # "NORMAL" | "PREFERENCIAL"
        "status": "AGUARDANDO",             # "AGUARDANDO" | "EM_ATENDIMENTO"
        "senha": senha,
        "createdAt": datetime.now(),
        "updatedAt": datetime.now(),
        "calledAt": None,
        "startedAt": None
    }

    pacientes.insert_one(paciente)
    return jsonify({"message": "Paciente cadastrado com sucesso"}), 201


@app.route("/api/fila", methods=["GET"])
@auth_required
def listar_fila():
    lista = list(
        pacientes.find({"status": {"$in": ["AGUARDANDO", "EM_ATENDIMENTO"]}})
        .sort([("tipo", -1), ("createdAt", 1)])
    )
    return jsonify([serializar(p) for p in lista]), 200


@app.route("/api/pacientes/<id>/chamar", methods=["PUT"])
@auth_required
def chamar_paciente(id):
    agora = datetime.now()

    paciente_clicado = pacientes.find_one({"_id": ObjectId(id)})
    if not paciente_clicado:
        return jsonify({"error": "Paciente não encontrado"}), 404

    if paciente_clicado.get("status") != "AGUARDANDO":
        return jsonify({"error": "Só é possível chamar pacientes com status AGUARDANDO."}), 400

    normal_seq = get_normal_seq()

    pref_mais_antigo = pacientes.find_one(
        {"status": "AGUARDANDO", "tipo": "PREFERENCIAL"},
        sort=[("createdAt", 1)]
    )

    paciente_para_chamar = paciente_clicado
    regra_aplicada = False

    # REGRA: a cada 2 normais, chama 1 preferencial (se existir aguardando)
    if (
        paciente_clicado.get("tipo") == "NORMAL"
        and pref_mais_antigo is not None
        and normal_seq >= 2
    ):
        paciente_para_chamar = pref_mais_antigo
        regra_aplicada = True

    # garante que ainda está aguardando
    result = pacientes.update_one(
        {"_id": paciente_para_chamar["_id"], "status": "AGUARDANDO"},
        {"$set": {
            "status": "EM_ATENDIMENTO",
            "calledAt": agora,
            "startedAt": agora,
            "updatedAt": agora
        }}
    )

    if result.matched_count == 0:
        return jsonify({"error": "Paciente já não está mais aguardando. Atualize a tela."}), 409

    if paciente_para_chamar.get("tipo") == "NORMAL":
        inc_normal_seq()
    else:
        reset_normal_seq()

    return jsonify({
        "message": "Paciente chamado",
        "regraPreferencialAplicada": regra_aplicada,
        "pacienteChamado": {
            "id": str(paciente_para_chamar["_id"]),
            "nome": paciente_para_chamar.get("nome"),
            "senha": paciente_para_chamar.get("senha"),
            "tipo": paciente_para_chamar.get("tipo")
        }
    }), 200


@app.route("/api/pacientes/<id>/finalizar", methods=["PUT"])
@auth_required
def finalizar_paciente(id):
    paciente = pacientes.find_one({"_id": ObjectId(id)})
    if not paciente:
        return jsonify({"error": "Paciente não encontrado"}), 404

    paciente["status"] = "FINALIZADO"
    paciente["finishedAt"] = datetime.now()
    paciente["updatedAt"] = datetime.now()

    historico.insert_one(paciente)
    pacientes.delete_one({"_id": ObjectId(id)})

    return jsonify({"message": "Atendimento finalizado"}), 200


@app.route("/api/historico", methods=["GET"])
@auth_required
def listar_historico():
    lista = list(historico.find().sort("finishedAt", -1))
    return jsonify([serializar(p) for p in lista]), 200


# =========================================================
# PACIENTE (PÚBLICO)
# =========================================================
@app.route("/api/paciente/login", methods=["POST"])
def paciente_login():
    dados = request.json or {}
    cpf = somente_numeros(dados.get("cpf"))

    if len(cpf) != 11:
        return jsonify({"error": "CPF inválido. Informe 11 dígitos."}), 400

    inicio, fim = inicio_fim_dia()

    paciente = pacientes.find_one({
        "cpf": cpf,
        "createdAt": {"$gte": inicio, "$lt": fim},
        "status": {"$in": ["AGUARDANDO", "EM_ATENDIMENTO"]}
    }, sort=[("createdAt", -1)])

    if not paciente:
        return jsonify({"error": "Nenhum atendimento ativo para este CPF hoje."}), 404

    return jsonify({"patientId": str(paciente["_id"])}), 200


@app.route("/api/paciente/status", methods=["GET"])
def paciente_status():
    patient_id = request.args.get("id")
    if not patient_id:
        return jsonify({"error": "ID do paciente ausente"}), 400

    try:
        paciente = pacientes.find_one({"_id": ObjectId(patient_id)})
    except:
        return jsonify({"error": "ID inválido"}), 400

    if not paciente:
        return jsonify({"error": "Atendimento não encontrado (pode ter finalizado)."}), 404

    agora = datetime.now()
    PREVISAO_POR_PESSOA_MIN = 10

    fila_geral = list(
        pacientes.find({"status": {"$in": ["AGUARDANDO", "EM_ATENDIMENTO"]}})
        .sort([("tipo", -1), ("createdAt", 1)])
    )

    idx = next((i for i, p in enumerate(fila_geral) if p["_id"] == paciente["_id"]), None)
    pessoas_na_frente = 0 if idx is None else idx

    aguardando_min = max(0, int((agora - paciente["createdAt"]).total_seconds() / 60))

    if paciente.get("status") == "EM_ATENDIMENTO":
        pessoas_na_frente = 0
        previsao_min = 0
    else:
        previsao_min = pessoas_na_frente * PREVISAO_POR_PESSOA_MIN

    return jsonify({
        "nome": paciente.get("nome"),
        "senha": paciente.get("senha"),
        "status": paciente.get("status"),
        "aguardandoMin": aguardando_min,
        "pessoasNaFrente": pessoas_na_frente,
        "previsaoMin": previsao_min
    }), 200


# =========================================================
# VISOR (PÚBLICO) - CORRIGIDO (SEM MISTURAR CHAMADOS/FINALIZADOS)
# =========================================================
@app.route("/api/visor/status", methods=["GET"])
def visor_status():
    agora = datetime.now()
    PREVISAO_POR_PACIENTE_MIN = 10

    # 🔹 Paciente atual (1 só)
    paciente_atual = pacientes.find_one(
        {"status": "EM_ATENDIMENTO"},
        sort=[("calledAt", -1)]
    )

    # 🔹 Fila aguardando
    fila = list(
        pacientes.find({"status": "AGUARDANDO"})
        .sort([("tipo", -1), ("createdAt", 1)])
    )

    lista_status = []
    for idx, p in enumerate(fila):
        aguardando_min = max(0, int((agora - p["createdAt"]).total_seconds() / 60))
        previsao_min = (idx + 1) * PREVISAO_POR_PACIENTE_MIN

        lista_status.append({
            "nome": p["nome"],
            "senha": p["senha"],
            "aguardandoMin": aguardando_min,
            "previsaoMin": previsao_min
        })

    # 🔹 Chamados recentemente (somente EM_ATENDIMENTO)
    chamados = list(
        pacientes.find({
            "status": "EM_ATENDIMENTO",
            "calledAt": {"$ne": None}
        })
        .sort("calledAt", -1)
        .limit(6)
    )

    # 🔹 Finalizados (somente do histórico)
    finalizados = list(
        historico.find()
        .sort("finishedAt", -1)
        .limit(5)
    )

    def minutos_desde(data):
        return max(0, int((agora - data).total_seconds() / 60))

    return jsonify({
        "pacienteAtual": {
            "nome": paciente_atual["nome"],
            "senha": paciente_atual["senha"]
        } if paciente_atual else None,

        "listaStatus": lista_status,

        "chamadosRecentes": [
            {
                "nome": c["nome"],
                "senha": c["senha"],
                "tempo": minutos_desde(c["calledAt"])
            }
            for c in chamados
            if not paciente_atual or c["_id"] != paciente_atual["_id"]
        ],

        "finalizados": [
            {
                "nome": f["nome"],
                "senha": f["senha"]
            }
            for f in finalizados
        ]
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
