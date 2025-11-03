// ===== Config =====
const API_BASE = ""; // mismo origen (http://localhost:5000)

// ===== Helpers =====
function toggleForm() {
  document.querySelectorAll(".form-container").forEach(el => el.classList.toggle("hidden"));
}
window.toggleForm = toggleForm;

function showAlert(msg) { alert(msg); }

// ===== Registro =====
const formRegister = document.getElementById("registro");
if (formRegister) {
  formRegister.addEventListener("submit", async (event) => {
    event.preventDefault();

    const data = Object.fromEntries(new FormData(formRegister).entries());
    if (!data.username || !data.password) {
      showAlert("Rellena usuario y contraseña.");
      return;
    }

    try {
      const resp = await fetch(`${API_BASE}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      });

      const json = await resp.json().catch(() => ({}));
      if (resp.status === 201) {
        showAlert("Registro correcto. Ahora inicia sesión.");
        toggleForm();
      } else {
        showAlert(json.error || "No se pudo registrar.");
      }
    } catch (err) {
      console.error("Error /register:", err);
      showAlert("No se pudo conectar con la API.");
    }
  });
}

// ===== Login =====
const formLogin = document.getElementById("inicio");
if (formLogin) {
  formLogin.addEventListener("submit", async (event) => {
    event.preventDefault();

    const data = Object.fromEntries(new FormData(formLogin).entries());
    if (!data.username || !data.password) {
      showAlert("Rellena usuario y contraseña.");
      return;
    }

    try {
      const resp = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      });

      const json = await resp.json().catch(() => ({}));
      if (resp.ok) {
        sessionStorage.setItem("animatch_user", JSON.stringify({
          username: json.username || data.username,
          role: json.role || "user"
        }));
        // ✅ Redirección correcta
        window.location.href = "/HTML/home.html";
      } else {
        showAlert(json.error || "Credenciales inválidas.");
      }
    } catch (err) {
      console.error("Error /login:", err);
      showAlert("No se pudo conectar con la API.");
    }
  });
}
