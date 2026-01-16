const API_BASE = "http://127.0.0.1:5000";

function somenteNumeros(v) {
  return (v || "").replace(/\D/g, "");
}

function setMsg(text) {
  const el = document.getElementById("msg");
  if (!el) return;
  el.textContent = text || "";
}

async function pacienteLogin(e) {
  e.preventDefault();
  setMsg("");

  const cpf = somenteNumeros(document.getElementById("cpf").value);

  if (!cpf || cpf.length !== 11) {
    setMsg("Digite um CPF válido (11 números).");
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/api/paciente/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cpf })
    });

    const data = await response.json();

    if (!response.ok) {
      setMsg(data.error || "CPF não encontrado hoje.");
      return;
    }

    localStorage.setItem("patientId", data.patientId);
    window.location.href = "paciente.html";

  } catch (err) {
    console.error(err);
    setMsg("Erro ao conectar com o servidor.");
  }
}

async function carregarStatusPaciente() {
  const patientId = localStorage.getItem("patientId");
  if (!patientId) {
    window.location.href = "paciente_login.html";
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/api/paciente/status?id=${encodeURIComponent(patientId)}`);
    const data = await response.json();

    if (!response.ok) {
      setMsg(data.error || "Não foi possível carregar seu status.");
      return;
    }

    const statusLabel = document.getElementById("statusLabel");
    if (statusLabel) statusLabel.textContent = (data.status || "").replace("_", " ");

    const senhaEl = document.getElementById("senha");
    if (senhaEl) senhaEl.textContent = data.senha || "---";

    const nomeEl = document.getElementById("nome");
    if (nomeEl) nomeEl.textContent = data.nome || "---";

    const tempoEl = document.getElementById("tempo");
    if (tempoEl) tempoEl.textContent = data.aguardandoMin ?? "--";

    const frenteEl = document.getElementById("frente");
    if (frenteEl) frenteEl.textContent = data.pessoasNaFrente ?? "--";

    const prevEl = document.getElementById("previsao");
    if (prevEl) prevEl.textContent = data.previsaoMin ?? "--";

    setMsg("");

  } catch (err) {
    console.error(err);
    setMsg("Erro ao conectar com o servidor.");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("form-paciente");
  if (form) form.addEventListener("submit", pacienteLogin);

  // pagina paciente.html
  if (document.getElementById("senha") && document.getElementById("frente")) {
    carregarStatusPaciente();
    setInterval(carregarStatusPaciente, 3000);
  }
});
