from database.mongo import atendimentos, historico
from datetime import datetime

TEMPO_MEDIO_PADRAO = 20  # minutos

def calcular_tempo_medio():
    registros = list(historico.find())
    if not registros:
        return TEMPO_MEDIO_PADRAO

    tempos = [r["duracao"] for r in registros]
    return int(sum(tempos) / len(tempos))


def gerar_posicao(tipo):
    fila = list(atendimentos.find({"status": "AGUARDANDO"}))
    return len(fila) + 1


def calcular_previsao(posicao):
    return posicao * calcular_tempo_medio()


def finalizar_atendimento(atendimento):
    fim = datetime.now()
    inicio = atendimento["inicio"]
    duracao = int((fim - inicio).total_seconds() / 60)

    historico.insert_one({
        "cpf": atendimento["cpf"],
        "tipo_atendimento": atendimento["tipo_atendimento"],
        "inicio": inicio,
        "fim": fim,
        "duracao": duracao
    })
