function toggleForm() {
        document.querySelectorAll('.form-container').forEach(el => el.classList.toggle('hidden'));
};

document.getElementById('registro').addEventListener('submit', function(event) {
  event.preventDefault(); // Evita el envío tradicional del formulario

  const form = event.target;
  const formData = new FormData(form);

  const data = Object.fromEntries(formData.entries());

  fetch('/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })
  .then(response => {
    if (!response.ok) throw new Error('Error en la respuesta');
    return response.json();
  })
  .then(result => {
    console.log('Respuesta del servidor:', result);
  })
  .catch(error => {
    console.error('Error en la petición:', error);
  });
});


