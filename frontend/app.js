let mediaRecorder;
let audioChunks = [];
let audioBlob = null;

const recordBtn = document.getElementById('recordBtn');
const sendBtn = document.getElementById('sendBtn');
const recordStatus = document.getElementById('recordStatus');
const audioPlayback = document.getElementById('audioPlayback');
const form = document.getElementById('audioForm');
const spinner = document.getElementById('spinner');
const resultsTable = document.getElementById('resultsTable').querySelector('tbody');
const audioFileInput = document.getElementById('audioFileInput');

let requestQueue = [];
let pendingCount = 0;
let lastGroqText = "";
let lastMistralText = "";
let currentLLM = "groq"; // Controla qual LLM está sendo lida (groq ou mistral)
let utterance = null;

// PAGINAÇÃO
let currentPage = 1;
let pageSize = 10;
let totalRecords = 0;

// Atualiza pageSize ao mudar o seletor
const pageSizeSelect = document.getElementById('pageSizeSelect');
if (pageSizeSelect) {
  pageSizeSelect.addEventListener('change', function () {
    pageSize = parseInt(this.value, 10);
    currentPage = 1;
    fetchAndRenderRecords();
  });
}

// Função para limpar texto para leitura
function cleanTextForSpeech(text) {
  return text
    .replace(/[*_`#>\[\]\(\)\-]/g, '') // Remove markdown
    .replace(/[\u{1F600}-\u{1F6FF}]/gu, '') // Remove emojis
    .replace(/[•●–—]/g, '') // Remove bullets/dashes
    .replace(/\s{2,}/g, ' ') // Remove múltiplos espaços
    .trim();
}

// Configura os controles globais de fala
function setupGlobalSpeechControls() {
  const switchLLMBtn = document.getElementById('btnSwitchLLM');
  const playPauseBtn = document.getElementById('btnPlayPause');
  const stopBtn = document.getElementById('btnStop');
  const speedControl = document.getElementById('speedControl');

  // Desabilita controles no início
  switchLLMBtn.disabled = true;
  playPauseBtn.disabled = true;
  stopBtn.disabled = true;
  speedControl.disabled = true;

  switchLLMBtn.onclick = function () {
    currentLLM = currentLLM === "groq" ? "mistral" : "groq";
    switchLLMBtn.textContent = currentLLM === "groq" ? "🔊 Ouvir Groq" : "🔊 Ouvir Mistral";
    window.speechSynthesis.cancel(); // Garante que a leitura anterior pare imediatamente
    playPauseBtn.textContent = "▶️ Play";
    playPauseBtn.disabled = false;
    stopBtn.disabled = false;
    speedControl.disabled = false;
    // Opcional: iniciar leitura automaticamente ao trocar LLM
    // playPauseBtn.click();
  };

  playPauseBtn.onclick = function () {
    if (window.speechSynthesis.speaking && !window.speechSynthesis.paused) {
      // Pausar
      window.speechSynthesis.pause();
      playPauseBtn.textContent = "▶️ Play";
    } else if (window.speechSynthesis.paused) {
      // Continuar
      window.speechSynthesis.resume();
      playPauseBtn.textContent = "⏸️ Pause";
    } else {
      // Sempre cria uma nova utterance ao dar play
      const text = cleanTextForSpeech(currentLLM === "groq" ? lastGroqText : lastMistralText);
      if (!text) return;
      utterance = new window.SpeechSynthesisUtterance(text);
      utterance.lang = "pt-BR";
      utterance.rate = parseFloat(speedControl.value);
      playPauseBtn.textContent = "⏸️ Pause";
      playPauseBtn.disabled = false;
      stopBtn.disabled = false;
      utterance.onend = () => {
        playPauseBtn.textContent = "▶️ Play";
      };
      utterance.onerror = () => {
        playPauseBtn.textContent = "▶️ Play";
      };
      window.speechSynthesis.speak(utterance);
    }
  };

  stopBtn.onclick = function () {
    window.speechSynthesis.cancel();
    playPauseBtn.textContent = "▶️ Play";
    // Permite novo play normalmente após parar
    // Não desabilita os controles
  };

  speedControl.oninput = function () {
    // Se estiver lendo ou pausado, apenas retoma a leitura após cancelar, sem reiniciar do início
    if (window.speechSynthesis.speaking || window.speechSynthesis.paused) {
      window.speechSynthesis.cancel();
      playPauseBtn.textContent = "▶️ Play";
      // Dá play automaticamente após cancelar
      playPauseBtn.click();
    }
  };
}

// Atualiza a tabela e paginação ao mudar o tamanho da página
function createPaginationControls() {
  let container = document.getElementById('paginationControls');
  if (!container) return;
  const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize));
  container.innerHTML = `
    <button id="prevPageBtn" ${currentPage === 1 ? "disabled" : ""} title="Página anterior">⟨</button>
    <span>Página ${currentPage} de ${totalPages} (${totalRecords} registros)</span>
    <button id="nextPageBtn" ${(currentPage >= totalPages) ? "disabled" : ""} title="Próxima página">⟩</button>
  `;
  document.getElementById('prevPageBtn').onclick = () => {
    if (currentPage > 1) {
      currentPage--;
      fetchAndRenderRecords();
    }
  };
  document.getElementById('nextPageBtn').onclick = () => {
    if (currentPage < totalPages) {
      currentPage++;
      fetchAndRenderRecords();
    }
  };
}

// Busca registros do backend
async function fetchAudioRecords(page = 1, size = 10) {
  const skip = (page - 1) * size;
  const url = `/api/audio_records/?skip=${skip}&limit=${size}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Erro ao buscar registros");
  return await res.json();
}

// Renderiza tabela
async function fetchAndRenderRecords() {
  spinner.style.display = "block";
  try {
    const data = await fetchAudioRecords(currentPage, pageSize);
    totalRecords = data.total;
    resultsTable.innerHTML = "";
    for (const r of data.items) {
      const row = resultsTable.insertRow();
      row.insertCell().outerHTML = `<td class="col-id">${r.id}</td>`;
      const statusCell = row.insertCell();
      statusCell.textContent = "OK";
      statusCell.className = "status-ok col-status";
      row.insertCell().outerHTML = `<td class="col-prompt">${r.prompt || ""}</td>`;
      row.insertCell().outerHTML = `<td class="col-trans">${r.transcription || ""}</td>`;
      row.insertCell().outerHTML = `<td class="col-groq">${cleanTextForSpeech(r.llm_groq || "")}</td>`;
      row.insertCell().outerHTML = `<td class="col-mistral">${cleanTextForSpeech(r.llm_mistral || "")}</td>`;
    }
    createPaginationControls();
  } catch (e) {
    resultsTable.innerHTML = `<tr><td colspan="6" style="color:red;">Erro ao carregar registros</td></tr>`;
  } finally {
    spinner.style.display = "none";
  }
}

// Atualiza/inclui registro no topo da tabela após envio
function insertOrUpdateTopRecord(data) {
  // Remove linha com mesmo ID se existir
  for (let i = 0; i < resultsTable.rows.length; i++) {
    if (resultsTable.rows[i].cells[0].textContent == data.id) {
      resultsTable.deleteRow(i);
      break;
    }
  }
  // Insere no topo
  const row = resultsTable.insertRow(0);
  row.insertCell().outerHTML = `<td class="col-id">${data.id}</td>`;
  const statusCell = row.insertCell();
  statusCell.textContent = "OK";
  statusCell.className = "status-ok col-status";
  row.insertCell().outerHTML = `<td class="col-prompt">${data.prompt || ""}</td>`;
  row.insertCell().outerHTML = `<td class="col-trans">${data.transcription || ""}</td>`;
  row.insertCell().outerHTML = `<td class="col-groq">${cleanTextForSpeech(data.llm_response_groq || "")}</td>`;
  row.insertCell().outerHTML = `<td class="col-mistral">${cleanTextForSpeech(data.llm_response_mistral || "")}</td>`;
}

form.onsubmit = async function (e) {
  e.preventDefault();
  // Permite envio se houver áudio gravado OU arquivo selecionado
  if (!audioBlob && !(audioFileInput.files && audioFileInput.files[0])) {
    alert("Grave um áudio ou selecione um arquivo antes de enviar.");
    return;
  }
  sendBtn.disabled = true;
  recordStatus.textContent = "Enviando...";

  // Adiciona à fila visual
  const id = document.getElementById('id').value || "1";
  const area = document.getElementById('area_especialista').value || "";
  const semestre_aluno = document.getElementById('semestre_aluno').value || "";  
  const sa = document.getElementById('sa_descricao').value || "";
  const etapa_descricao = document.getElementById('etapa_descricao').value || "";
  const pratica = document.getElementById('pratica_descricao').value || "";
  const parametros_descricao = document.getElementById('parametros_descricao').value || "";
  const row = resultsTable.insertRow();
  row.insertCell().textContent = id;
  const statusCell = row.insertCell();
  statusCell.textContent = "Processando...";
  statusCell.className = "status-processing";
  const promptCell = row.insertCell();
  promptCell.textContent = "";
  const transCell = row.insertCell();
  transCell.textContent = "";
  const groqCell = row.insertCell();
  groqCell.textContent = "";
  const mistralCell = row.insertCell();
  mistralCell.textContent = "";

  pendingCount++;
  spinner.style.display = "block";

  const formData = new FormData();
  formData.append("id", id);
  formData.append("area_especialista", area);
  formData.append("semestre_aluno", semestre_aluno);  
  formData.append("sa_descricao", sa);
  formData.append("etapa_descricao", etapa_descricao);
  formData.append("pratica_descricao", pratica);
  formData.append("parametros_descricao", parametros_descricao);

  // Usa o arquivo selecionado ou o áudio gravado
  if (audioFileInput.files && audioFileInput.files[0]) {
    formData.append("file", audioFileInput.files[0], audioFileInput.files[0].name);
  } else if (audioBlob) {
    formData.append("file", audioBlob, "audio.webm");
  }

  // Limpa seleção/gravação para novo envio
  audioBlob = null;
  audioPlayback.src = "";
  audioPlayback.style.display = "none";
  audioFileInput.value = "";
  recordStatus.textContent = "";

  // Habilita para novo envio imediatamente
  sendBtn.disabled = false;

  // Desabilita controles antes de enviar
  document.getElementById('btnSwitchLLM').disabled = true;
  document.getElementById('btnPlayPause').disabled = true;
  document.getElementById('btnStop').disabled = true;
  document.getElementById('speedControl').disabled = true;

  fetch("/api/avaliacao/", {
    method: "POST",
    body: formData
  })
    .then(async res => {
      let data;
      try {
        data = await res.json();
      } catch {
        data = { detail: "Resposta inválida da API" };
      }
      if (!res.ok) {
        statusCell.textContent = "Erro: " + (data.detail || res.statusText);
        statusCell.className = "status-error";
      } else {
        statusCell.textContent = "OK";
        statusCell.className = "status-ok";
        promptCell.textContent = data.prompt || "";
        transCell.textContent = data.transcription || "";
        groqCell.textContent = cleanTextForSpeech(data.llm_response_groq || "");
        mistralCell.textContent = cleanTextForSpeech(data.llm_response_mistral || "");
        lastGroqText = cleanTextForSpeech(data.llm_response_groq || "");
        lastMistralText = cleanTextForSpeech(data.llm_response_mistral || "");
        document.getElementById('btnPlayPause').disabled = false;
        document.getElementById('btnStop').disabled = false;

        // Habilita controles após resposta
        document.getElementById('btnSwitchLLM').disabled = false;
        document.getElementById('btnPlayPause').disabled = false;
        document.getElementById('btnStop').disabled = false;
        document.getElementById('speedControl').disabled = false;

        // Dá play automaticamente no Groq
        currentLLM = "groq";
        document.getElementById('btnSwitchLLM').textContent = "🔊 Ouvir Groq";
        document.getElementById('btnPlayPause').click();

        // Atualiza tabela: insere/atualiza registro no topo
        insertOrUpdateTopRecord(data);
      }
    })
    .catch(err => {
      statusCell.textContent = "Erro: " + err.message;
      statusCell.className = "status-error";
    })
    .finally(() => {
      pendingCount--;
      if (pendingCount <= 0) spinner.style.display = "none";
    });
};

audioFileInput.onchange = function(e) {
  const file = e.target.files[0];
  if (file) {
    audioBlob = null; // Limpa áudio gravado ao escolher arquivo
    audioPlayback.src = URL.createObjectURL(file);
    audioPlayback.style.display = "block";
    sendBtn.disabled = false;
    recordStatus.textContent = "Arquivo selecionado: " + file.name;
    // Limpa gravação visualmente
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      recordBtn.textContent = "Gravar Áudio";
      recordStatus.textContent = "Arquivo selecionado: " + file.name;
    }
  } else {
    audioPlayback.style.display = "none";
    sendBtn.disabled = true;
    recordStatus.textContent = "";
  }
};

recordBtn.onclick = async function() {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
    recordBtn.textContent = "Gravar Áudio";
    recordStatus.textContent = "Gravação finalizada.";
    sendBtn.disabled = false;
    audioFileInput.value = ""; // Limpa seleção de arquivo ao gravar
    return;
  }

  if (!navigator.mediaDevices) {
    alert("Seu navegador não suporta gravação de áudio.");
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    mediaRecorder.ondataavailable = e => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };
    mediaRecorder.onstop = () => {
      audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
      audioPlayback.src = URL.createObjectURL(audioBlob);
      audioPlayback.style.display = "block";
      sendBtn.disabled = false;
      audioFileInput.value = ""; // Limpa seleção de arquivo ao gravar novo áudio
      // Limpa seleção de arquivo visualmente
      if (audioFileInput.files && audioFileInput.files.length > 0) {
        audioFileInput.value = "";
      }
      recordStatus.textContent = "Gravação finalizada.";
    };
    mediaRecorder.start();
    recordBtn.textContent = "Parar Gravação";
    recordStatus.textContent = "Gravando...";
    sendBtn.disabled = true;
    // Limpa seleção de arquivo ao iniciar gravação
    audioFileInput.value = "";
  } catch (err) {
    alert("Erro ao acessar o microfone: " + err.message);
  }
};

// Inicializa controles globais após DOM carregado
window.addEventListener('DOMContentLoaded', () => {
  setupGlobalSpeechControls();
  document.getElementById('btnPlayPause').disabled = true;
  document.getElementById('btnStop').disabled = true;
  fetchAndRenderRecords();
});

// Adiciona evento para puxar Groq/Mistral para o controle de áudio ao clicar na célula correspondente
resultsTable.parentElement.addEventListener('click', function (event) {
  // ...lógica já existente para col-trans pode ficar aqui se desejar...

  // Groq
  const groqCell = event.target.closest('td.col-groq');
  if (groqCell) {
    const text = groqCell.textContent.trim();
    if (text) {
      lastGroqText = text;
      currentLLM = "groq";
      document.getElementById('btnSwitchLLM').textContent = "🔊 Ouvir Groq";
      document.getElementById('btnPlayPause').disabled = false;
      document.getElementById('btnStop').disabled = false;
      document.getElementById('btnSwitchLLM').disabled = false;
      document.getElementById('speedControl').disabled = false;
      document.getElementById('btnPlayPause').textContent = "⏸️ Pause";
      // Dispara o play automático
      if (window.speechSynthesis.speaking) window.speechSynthesis.cancel();
      document.getElementById('btnPlayPause').click();
    }
    return;
  }

  // Mistral
  const mistralCell = event.target.closest('td.col-mistral');
  if (mistralCell) {
    const text = mistralCell.textContent.trim();
    if (text) {
      lastMistralText = text;
      currentLLM = "mistral";
      document.getElementById('btnSwitchLLM').textContent = "🔊 Ouvir Mistral";
      document.getElementById('btnPlayPause').disabled = false;
      document.getElementById('btnStop').disabled = false;
      document.getElementById('btnSwitchLLM').disabled = false;
      document.getElementById('speedControl').disabled = false;
      document.getElementById('btnPlayPause').textContent = "⏸️ Pause";
      if (window.speechSynthesis.speaking) window.speechSynthesis.cancel();
      document.getElementById('btnPlayPause').click();
    }
    return;
  }
});
