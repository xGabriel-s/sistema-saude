

const BASE_URL = "http://127.0.0.1:5000";

const ROUTES = {
  criar: `${BASE_URL}/api/pacientes`,
  fila: `${BASE_URL}/api/fila`,
  chamar: `${BASE_URL}/api/pacientes/{id}/chamar`,
  finalizar: `${BASE_URL}/api/pacientes/{id}/finalizar`,
  historico: `${BASE_URL}/api/historico`,
  visorStatus: `${BASE_URL}/api/visor/status`
};

// ===============================
// AUTH HELPERS
// ===============================
function getToken() {
  return localStorage.getItem("authToken");
}

function authHeaders() {
  const token = getToken();
  return {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${token}`
  };
}

function redirectToLogin() {
  // ajuste se seu arquivo tiver outro nome/caminho
  window.location.href = "login.html";
}

async function fetchAuthed(url, options = {}) {
  const token = getToken();

  // se não tem token e está na tela do atendente, manda pro login
  if (!token && document.getElementById("form-cadastro")) {
    redirectToLogin();
    throw new Error("Sem token");
  }

  const res = await fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      ...authHeaders()
    }
  });

  // Se token inválido/expirado
  if (res.status === 401) {
    localStorage.removeItem("authToken");
    redirectToLogin();
    throw new Error("Não autorizado");
  }

  return res;
}

// ===============================
// UI HELPERS
// ===============================
function exibirMensagem(containerId, mensagem, tipo = 'error') {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = `
    <div class="message message-${tipo}">
      ${mensagem}
    </div>
  `;

  setTimeout(() => {
    container.innerHTML = '';
  }, 5000);
}

function formatarCPF(cpf) {
  if (!cpf) return '-';
  const limpo = cpf.replace(/\D/g, '');
  if (limpo.length >= 11) {
    return `${limpo.substring(0, 3)}.***.**-${limpo.substring(9, 11)}`;
  }
  return cpf;
}

function getStatusBadgeClass(status) {
  const statusMap = {
    'aguardando': 'badge-aguardando',
    'em_atendimento': 'badge-em-atendimento',
    'em atendimento': 'badge-em-atendimento',
    'finalizado': 'badge-finalizado'
  };
  return statusMap[status?.toLowerCase()] || 'badge-aguardando';
}

function formatarStatus(status) {
  const statusMap = {
    'aguardando': 'Aguardando',
    'em_atendimento': 'Em Atendimento',
    'em atendimento': 'Em Atendimento',
    'finalizado': 'Finalizado'
  };
  return statusMap[status?.toLowerCase()] || status || 'Aguardando';
}

// ===============================
// ATENDENTE
// ===============================
async function carregarFila() {
  const tbody = document.getElementById('fila-tbody');
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="7" class="loading">Carregando fila...</td></tr>';

  try {
    const response = await fetchAuthed(ROUTES.fila, { method: 'GET' });

    if (!response.ok) throw new Error(`Erro ${response.status}: ${response.statusText}`);

    const dados = await response.json();
    renderizarFila(dados);
  } catch (error) {
    console.error('Erro ao carregar fila:', error);
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="empty-state">
          <p>Erro ao carregar fila. Verifique a conexão com o backend.</p>
          <p style="font-size: 0.8rem; margin-top: 10px;">${error.message}</p>
        </td>
      </tr>
    `;
  }
}

function renderizarFila(pacientes) {
  const tbody = document.getElementById('fila-tbody');
  if (!tbody) return;

  if (!pacientes || pacientes.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="empty-state">
          <p>Nenhum paciente na fila</p>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = pacientes.map(p => `
    <tr>
      <td>${p.nome || '-'}</td>
      <td>${formatarCPF(p.cpf)}</td>
      <td>${p.telefone || '-'}</td>
      <td>
        <span class="badge ${p.tipo === 'PREFERENCIAL' ? 'badge-preferencial' : 'badge-normal'}">
          ${p.tipo || 'NORMAL'}
        </span>
      </td>
      <td>
        <span class="badge ${getStatusBadgeClass(p.status)}">
          ${formatarStatus(p.status)}
        </span>
      </td>
      <td>${p.previsao ? p.previsao + ' min' : '-'}</td>
      <td class="actions">
        <button class="btn btn-success btn-sm" onclick="chamarPaciente('${p.id}')">
          Chamar
        </button>
        <button class="btn btn-warning btn-sm" onclick="finalizarPaciente('${p.id}')">
          Finalizar
        </button>
      </td>
    </tr>
  `).join('');
}

async function carregarHistorico() {
  const tbody = document.getElementById('historico-tbody');
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="5" class="loading">Carregando histórico...</td></tr>';

  try {
    const response = await fetchAuthed(ROUTES.historico, { method: 'GET' });

    if (!response.ok) throw new Error(`Erro ${response.status}: ${response.statusText}`);

    const dados = await response.json();
    renderizarHistorico(dados);
  } catch (error) {
    console.error('Erro ao carregar histórico:', error);
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="empty-state">
          <p>Erro ao carregar histórico.</p>
        </td>
      </tr>
    `;
  }
}

function renderizarHistorico(pacientes) {
  const tbody = document.getElementById('historico-tbody');
  if (!tbody) return;

  if (!pacientes || pacientes.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="empty-state">
          <p>Nenhum atendimento no histórico</p>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = pacientes.map(p => `
    <tr>
      <td>${p.nome || '-'}</td>
      <td>${formatarCPF(p.cpf)}</td>
      <td>${p.telefone || '-'}</td>
      <td>
        <span class="badge ${p.tipo === 'PREFERENCIAL' ? 'badge-preferencial' : 'badge-normal'}">
          ${p.tipo || 'NORMAL'}
        </span>
      </td>
      <td>${p.senha || '-'}</td>
    </tr>
  `).join('');
}

async function cadastrarPaciente(event) {
  event.preventDefault();

  const form = document.getElementById('form-cadastro');
  if (!form) return;

  const dados = {
    nome: document.getElementById('nome').value.trim(),
    cpf: document.getElementById('cpf').value.trim(),
    telefone: document.getElementById('telefone').value.trim(),
    idade: parseInt(document.getElementById('idade').value, 10),
    tipo: document.getElementById('tipo').value
  };

  if (!dados.nome || !dados.cpf || !dados.telefone || !dados.idade || !dados.tipo) {
    exibirMensagem('mensagem-container', 'Preencha todos os campos obrigatórios.', 'error');
    return;
  }

  try {
    const response = await fetchAuthed(ROUTES.criar, {
      method: 'POST',
      body: JSON.stringify(dados)
    });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(payload.error || `Erro ${response.status}: ${response.statusText}`);
    }

    form.reset();
    exibirMensagem('mensagem-container', 'Paciente cadastrado com sucesso!', 'success');

    await Promise.all([carregarFila(), carregarHistorico()]);
  } catch (error) {
    console.error('Erro ao cadastrar paciente:', error);
    exibirMensagem('mensagem-container', `Erro ao cadastrar: ${error.message}`, 'error');
  }
}

async function chamarPaciente(id) {
  if (!id) return;

  const url = ROUTES.chamar.replace('{id}', id);

  try {
    const response = await fetchAuthed(url, { method: 'PUT' });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(payload.error || `Erro ${response.status}: ${response.statusText}`);
    }

    exibirMensagem('mensagem-container', 'Paciente chamado!', 'success');
    await carregarFila();
  } catch (error) {
    console.error('Erro ao chamar paciente:', error);
    exibirMensagem('mensagem-container', `Erro ao chamar: ${error.message}`, 'error');
  }
}

async function finalizarPaciente(id) {
  if (!id) return;

  const url = ROUTES.finalizar.replace('{id}', id);

  try {
    const response = await fetchAuthed(url, { method: 'PUT' });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(payload.error || `Erro ${response.status}: ${response.statusText}`);
    }

    exibirMensagem('mensagem-container', 'Atendimento finalizado!', 'success');
    await Promise.all([carregarFila(), carregarHistorico()]);
  } catch (error) {
    console.error('Erro ao finalizar paciente:', error);
    exibirMensagem('mensagem-container', `Erro ao finalizar: ${error.message}`, 'error');
  }
}

// ===============================
// VISOR (PÚBLICO)
// ===============================
async function atualizarVisor() {
  try {
    const response = await fetch(ROUTES.visorStatus, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) throw new Error(`Erro ${response.status}: ${response.statusText}`);

    const dados = await response.json();
    renderizarVisor(dados);
  } catch (error) {
    console.error('Erro ao atualizar visor:', error);
    renderizarVisorVazio();
  }
}

function renderizarVisor(dados) {
  const chamadaContainer = document.getElementById("chamada-atual");

  const filaLista = document.getElementById("visor-fila");
  const chamadosLista = document.getElementById("visor-historico"); // chamados recentes
  const finalizadosLista = document.getElementById("visor-finalizados");

  // =========================
  // CHAMADA ATUAL (CENTRO)
  // =========================
  if (chamadaContainer) {
    if (dados.pacienteAtual && dados.pacienteAtual.nome) {
      chamadaContainer.className = "chamada-atual";
      chamadaContainer.innerHTML = `
        <div class="label">Chamando</div>
        <div class="senha">${dados.pacienteAtual.senha || "S/N"}</div>
        <div class="nome">${dados.pacienteAtual.nome}</div>
      `;
    } else {
      renderizarVisorVazio();
    }
  }

  // =========================
  // AGUARDANDO ATENDIMENTO
  // =========================
  if (filaLista) {
    const lista = (dados.listaStatus || []).slice(0, 4);

    filaLista.innerHTML = lista.length === 0
      ? `<li class="empty-state"><p>Nenhum paciente aguardando</p></li>`
      : lista.map(p => `
          <li>
            <div>
              <div class="nome-visor">${p.nome}</div>
              <div class="sub-visor">
                Aguardando ${p.aguardandoMin} min • Previsão ${p.previsaoMin} min
              </div>
            </div>
            <span class="senha-visor">${p.senha}</span>
          </li>
        `).join("");
  }

  // =========================
  // CHAMADOS RECENTEMENTE
  // =========================
  if (chamadosLista) {
    const lista = (dados.chamadosRecentes || []).slice(0, 4);

    chamadosLista.innerHTML = lista.length === 0
      ? `<li class="empty-state"><p>Nenhum chamado recente</p></li>`
      : lista.map(p => `
          <li>
            <div>
              <div class="nome-visor">${p.nome}</div>
              <div class="sub-visor">Chamado há ${p.tempo} min</div>
            </div>
            <span class="senha-visor">${p.senha}</span>
          </li>
        `).join("");
  }

  // =========================
  // FINALIZADOS
  // =========================
  if (finalizadosLista) {
    const lista = (dados.finalizados || []).slice(0, 5);

    finalizadosLista.innerHTML = lista.length === 0
      ? `<li class="empty-state"><p>Nenhum atendimento finalizado</p></li>`
      : lista.map(p => `
          <li>
            <span class="nome-visor">${p.nome}</span>
            <span class="senha-visor">${p.senha}</span>
          </li>
        `).join("");
  }
}



function renderizarVisorVazio() {
  const chamadaContainer = document.getElementById('chamada-atual');
  if (chamadaContainer) {
    chamadaContainer.className = 'chamada-atual vazio';
    chamadaContainer.innerHTML = `
      <div class="label">Aguardando</div>
      <div class="senha">---</div>
      <div class="nome">Nenhum paciente em atendimento</div>
    `;
  }
}

function iniciarPollingVisor() {
  atualizarVisor();
  setInterval(atualizarVisor, 3000);
}

// ===============================
// INIT
// ===============================
function initAtendente() {
  const form = document.getElementById('form-cadastro');
  if (form) form.addEventListener('submit', cadastrarPaciente);

  carregarFila();
  carregarHistorico();
}

function initVisor() {
  iniciarPollingVisor();
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('form-cadastro')) initAtendente();
  if (document.getElementById('chamada-atual')) initVisor();
});
