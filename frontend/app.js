let mediaRecorder;
let audioChunks = [];
let audioBlob = null;

const recordBtn = document.getElementById('recordBtn');
const sendBtn = document.getElementById('sendBtn');
const recordStatus = document.getElementById('recordStatus');
const audioPlayback = document.getElementById('audioPlayback');
const form = document.getElementById('audioForm');
const responseDiv = document.getElementById('response');

recordBtn.onclick = async function() {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
    recordBtn.textContent = "Gravar Áudio";
    recordStatus.textContent = "Gravação finalizada.";
    sendBtn.disabled = false;
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
    alert("Grave um áudio antes de enviar.");
    return;
  }
  sendBtn.disabled = true;
  recordStatus.textContent = "Enviando...";
  responseDiv.textContent = "";

  const formData = new FormData();
  formData.append("id", document.getElementById('id').value || "1");
  formData.append("llm", document.getElementById('llm').value || "groq");
  formData.append("file", audioBlob, "audio.webm");

  try {
    const res = await fetch("http://localhost:8000/upload/", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (!res.ok) {
      responseDiv.textContent = "Erro: " + (data.detail || res.statusText);
    } else {
      responseDiv.textContent = JSON.stringify(data, null, 2);
    }
  } catch (err) {
    responseDiv.textContent = "Erro ao enviar: " + err.message;
  }
  recordStatus.textContent = "";
  sendBtn.disabled = false;
};
