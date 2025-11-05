const API_BASE = ""; // mismo origen (ej: http://localhost:5000)

document.addEventListener("DOMContentLoaded", () => {
  // --- Referencias UI principales ---
  const userBox   = document.getElementById("userInfo");
  const adminBox  = document.getElementById("adminTools");
  const logout    = document.getElementById("logoutLink");
  const form      = document.getElementById("formulario");
  const clearBtn  = document.getElementById("clearBtn");
  const retrainBtn= document.getElementById("retrainBtn");
  const out       = document.getElementById("resultado");

  // --- Sesión de usuario ---
  let user = null;
  try { user = JSON.parse(sessionStorage.getItem("animatch_user") || "{}"); } catch {}
  if (!user || !user.username) {
    window.location.href = "/"; // vuelve a auth
    return;
  }

  // Pinta info usuario
  userBox.textContent = `Usuario: ${user.username} (rol: ${user.role || "user"})`;

  // Toggle herramientas de admin
  if (user.role === "admin") {
    adminBox.style.display = "block";
  } else {
    adminBox.style.display = "none";
  }

  // --- Logout ---
  if (logout) {
    logout.addEventListener("click", (e) => {
      e.preventDefault();
      try { sessionStorage.removeItem("animatch_user"); } catch {}
      window.location.href = "/";
    });
  }

  // --- Helpers de UI ---
  function ensureSuggestionsList() {
    let ul = document.getElementById("suggestions");
    if (!ul) {
      ul = document.createElement("ul");
      ul.id = "suggestions";
      ul.className = "hidden";
      ul.style.marginTop = ".5rem";
      // lo colocamos debajo del formulario
      form.parentElement.insertBefore(ul, out);
    }
    return ul;
  }

  function setNotice(msg, type = "info") {
    const el = document.getElementById("msg");
    if (!el) return;
    el.textContent = msg;
    el.className = `notice ${type}`;
  }

  function readAnimeInputs() {
    // Soporta tanto (anime_1, anime_2) como (anime_id_1, anime_id_2)
    const getVal = (nameA, nameB) => {
      const a = form.querySelector(`[name="${nameA}"]`);
      const b = form.querySelector(`[name="${nameB}"]`);
      const v = (a?.value || b?.value || "").trim();
      return v;
    };
    const a1 = getVal("anime_1", "anime_id_1");
    const a2 = getVal("anime_2", "anime_id_2");
    const r1 = parseFloat(form.querySelector('[name="rating_1"]')?.value || "");
    const r2 = parseFloat(form.querySelector('[name="rating_2"]')?.value || "");
    return { a1, a2, r1, r2 };
  }

  function renderConflicts(conflicts) {
    // conflicts: { "textoOriginal": [{id,name}, ...], ... }
    const ul = ensureSuggestionsList();
    ul.innerHTML = "";

    Object.entries(conflicts).forEach(([original, cands]) => {
      const title = document.createElement("li");
      title.innerHTML = `<strong>“${original}”</strong> podría ser:`;
      ul.appendChild(title);

      cands.forEach(c => {
        const li = document.createElement("li");
        li.style.cursor = "pointer";
        li.textContent = `${c.name} (id: ${c.id})`;
        li.addEventListener("click", () => {
          // Sustituye en el formulario el texto original por el ID seleccionado y guía al usuario
          const inp1 = form.querySelector('[name="anime_1"]') || form.querySelector('[name="anime_id_1"]');
          const inp2 = form.querySelector('[name="anime_2"]') || form.querySelector('[name="anime_id_2"]');
          if (inp1 && inp1.value.trim().toLowerCase() === original.toLowerCase()) inp1.value = String(c.id);
          else if (inp2 && inp2.value.trim().toLowerCase() === original.toLowerCase()) inp2.value = String(c.id);
          ul.classList.add("hidden");
          setNotice(`Seleccionado: ${c.name} (id ${c.id}). Pulsa "Recomendar".`, "success");
        });
        ul.appendChild(li);
      });

      const sep = document.createElement("li");
      sep.innerHTML = "<hr/>";
      ul.appendChild(sep);
    });

    ul.classList.remove("hidden");
  }

  // --- Submit: obtener recomendaciones (admite nombre o id) ---
  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const { a1, a2, r1, r2 } = readAnimeInputs();

    if (!a1 || !a2) { setNotice("Escribe el nombre o id de los dos animes.", "error"); return; }
    if ([r1, r2].some(Number.isNaN)) { setNotice("Las notas deben ser números.", "error"); return; }
    if (![r1, r2].every(v => v >= 1 && v <= 10)) { setNotice("Las notas deben estar entre 1 y 10.", "error"); return; }

    // Payload mixto: claves pueden ser nombre o id
    const payload = {}; payload[a1] = r1; payload[a2] = r2;

    setNotice("Calculando recomendaciones...", "info");
    ensureSuggestionsList().classList.add("hidden");
    out.innerHTML = "";

    try {
      const resp = await fetch(`${API_BASE}/obtener-recomendaciones`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await resp.json().catch(() => ({}));

      if (resp.status === 404) {
        setNotice(data.error || "No se encontró alguno de los animes.", "error");
        return;
      }
      if (resp.status === 409 && data.conflicts) {
        setNotice("Hay múltiples coincidencias. Elige la correcta.", "info");
        renderConflicts(data.conflicts);
        return;
      }
      if (!resp.ok) {
        setNotice(data.error || "Error al obtener recomendaciones.", "error");
        return;
      }

      setNotice("Recomendaciones listas.", "success");
      const rows = (Array.isArray(data) ? data : []).map(rec => {
        const aid   = rec.anime_id ?? "";
        const name  = rec.name ?? "(sin nombre)";
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
      setNotice("No se pudo conectar con la API.", "error");
    }
  });

  // --- Limpiar formulario ---
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      form.reset();
      out.innerHTML = "";
      ensureSuggestionsList().classList.add("hidden");
      setNotice("Introduce dos animes y sus notas (1–10).", "info");
    });
  }

  // --- Retrain (solo admin) ---
  if (retrainBtn && user.role === "admin") {
    retrainBtn.addEventListener("click", async () => {
      // Pedimos contraseña por seguridad (no asumimos que esté en sessionStorage)
      const pwd = prompt("Introduce tu contraseña para reentrenar el modelo (admin):") || "";
      if (!pwd) { setNotice("Operación cancelada.", "info"); return; }

      setNotice("Reentrenando modelo...", "info");
      try {
        const r = await fetch(`${API_BASE}/retrain`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: user.username, password: pwd })
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
});
