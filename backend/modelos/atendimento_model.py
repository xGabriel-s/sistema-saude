from datetime import datetime

def criar_atendimento(data, posicao, previsao):
    return {
        "nome": data["nome"],
        "cpf": data["cpf"],
        "telefone": data["telefone"],
        "tipo_atendimento": data["tipo_atendimento"],  # NORMAL | PREFERENCIAL
        "status": "AGUARDANDO",
        "posicao": posicao,
        "previsao_minutos": previsao,
        "entrada": datetime.now(),
        "inicio": None,
        "fim": None
    }
