document.getElementById('formulario').addEventListener('submit', function(event) {
    event.preventDefault()

    const form = new FormData(this);
    const data = {
        anime_id: form.get("anime"),
        puntuacion: form.get("puntuacion")
    };

  fetch('http://localhost:5000/obtener-recomendaciones', {
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


