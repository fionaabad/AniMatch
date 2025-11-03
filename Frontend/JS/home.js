const API_BASE = ""; // mismo origen (http://localhost:5000)

document.addEventListener("DOMContentLoaded", () => {
  const userBox  = document.getElementById("userInfo");
  const adminBox = document.getElementById("adminTools");
  const logout   = document.getElementById("logoutLink");

  let user = null;
  try { user = JSON.parse(sessionStorage.getItem("animatch_user") || "{}"); } catch {}

  if (!user || !user.username) {
    window.location.href = "/"; // vuelve a auth
    return;
  }

  userBox.textContent = `Usuario: ${user.username} (rol: ${user.role || "user"})`;
  if (user.role === "admin") adminBox.style.display = "block";

  // ✅ Logout: borra sesión y vuelve a auth
  logout.addEventListener("click", (e) => {
    e.preventDefault();
    sessionStorage.removeItem("animatch_user");
    window.location.href = "/";
  });

  // Retrain (admin)
  const retrainBtn = document.getElementById("retrainBtn");
  if (retrainBtn) {
    retrainBtn.addEventListener("click", async () => {
      const pw = prompt("Confirma contraseña admin:");
      if (!pw) return;

      const payload = { username: user.username, password: pw };
      setNotice("Reentrenando modelo... puede tardar unos segundos.", "info");
      try {
        const r = await fetch(`${API_BASE}/retrain`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await r.json().catch(() => ({}));
        if (r.ok) setNotice(data.message || "Modelo reentrenado correctamente.", "success");
        else setNotice(data.error || "No autorizado o error al reentrenar.", "error");
      } catch (err) {
        console.error(err);
        setNotice("No se pudo conectar con la API.", "error");
      }
    });
  }

  // Limpiar
  document.getElementById("clearBtn").addEventListener("click", () => {
    document.getElementById("formulario").reset();
    document.getElementById("resultado").innerHTML = "";
    setNotice("Introduce dos animes y sus notas (1–10).", "info");
  });
});

function setNotice(text, kind = "info") {
  const el = document.getElementById("msg");
  el.className = `notice ${kind}`;
  el.textContent = text;
}

document.getElementById("formulario").addEventListener("submit", async function (event) {
  event.preventDefault();

  const form = new FormData(this);
  const a1 = parseInt(form.get("anime_id_1"), 10);
  const r1 = parseFloat(form.get("rating_1"));
  const a2 = parseInt(form.get("anime_id_2"), 10);
  const r2 = parseFloat(form.get("rating_2"));

  if ([a1, a2].some(Number.isNaN) || [r1, r2].some(Number.isNaN)) {
    setNotice("IDs y notas deben ser números.", "error"); return;
  }
  if (![r1, r2].every(v => v >= 1 && v <= 10)) {
    setNotice("Las notas deben estar entre 1 y 10.", "error"); return;
  }

  const payload = {}; payload[a1] = r1; payload[a2] = r2;
  setNotice("Calculando recomendaciones...", "info");

  try {
    const resp = await fetch(`${API_BASE}/obtener-recomendaciones`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await resp.json().catch(() => ([]));
    const out  = document.getElementById("resultado");

    if (!resp.ok) { setNotice(data.error || "Error al obtener recomendaciones.", "error"); out.innerHTML=""; return; }
    if (!Array.isArray(data) || data.length === 0) { setNotice("Sin resultados. Prueba con otros animes.", "info"); out.innerHTML=""; return; }

    setNotice("Recomendaciones listas.", "success");
    const rows = data.map(rec => {
      const aid = rec.anime_id ?? "";
      const name = rec.name ?? "(sin nombre)";
      const score = typeof rec.score === "number" ? rec.score.toFixed(2) : rec.score;
      return `<tr><td>${aid}</td><td>${name}</td><td>${score}</td></tr>`;
    }).join("");

    out.innerHTML = `
      <table class="table">
        <thead><tr><th>anime_id</th><th>name</th><th>score</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  } catch (error) {
    console.error(error);
    setNotice('No se pudo conectar con la API.', 'error');
  }
});
