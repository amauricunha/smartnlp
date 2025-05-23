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

audioFileInput.onchange = function(e) {
  const file = e.target.files[0];
  if (file) {
    audioBlob = file;
    audioPlayback.src = URL.createObjectURL(file);
    audioPlayback.style.display = "block";
    sendBtn.disabled = false;
    recordStatus.textContent = "Arquivo selecionado: " + file.name;
  } else {
    audioBlob = null;
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
    };
    mediaRecorder.start();
    recordBtn.textContent = "Parar Gravação";
    recordStatus.textContent = "Gravando...";
    sendBtn.disabled = true;
  } catch (err) {
    alert("Erro ao acessar o microfone: " + err.message);
  }
};

form.onsubmit = async function(e) {
  e.preventDefault();
  if (!audioBlob) {
    alert("Grave um áudio ou selecione um arquivo antes de enviar.");
    return;
  }
  sendBtn.disabled = true;
  recordStatus.textContent = "Enviando...";

  // Adiciona à fila visual
  const id = document.getElementById('id').value || "1";
  const pratica = document.getElementById('pratica_descricao').value || "";
  const sa = document.getElementById('sa_descricao').value || "";
  const row = resultsTable.insertRow();
  row.insertCell().textContent = id;
  const statusCell = row.insertCell();
  statusCell.textContent = "Processando...";
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
  formData.append("pratica_descricao", pratica);
  formData.append("sa_descricao", sa);

  // Usa o arquivo selecionado ou o áudio gravado
  if (audioFileInput.files[0]) {
    formData.append("file", audioFileInput.files[0], audioFileInput.files[0].name);
  } else {
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

  fetch("http://localhost:8000/avaliacao/", {
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
      } else {
        statusCell.textContent = "OK";
        transCell.textContent = data.transcription || "";
        groqCell.textContent = data.llm_response_groq || "";
        mistralCell.textContent = data.llm_response_mistral || "";
      }
    })
    .catch(err => {
      statusCell.textContent = "Erro: " + err.message;
    })
    .finally(() => {
      pendingCount--;
      if (pendingCount <= 0) spinner.style.display = "none";
      // Não mexe mais em sendBtn aqui, pois já foi habilitado acima
    });
};
