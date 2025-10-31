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
    const tabla = document.createElement("table")
    const cabezera = document.createElement("thead")
    const columna_1 = document.createElement("tr")
    const columna_2= document.createElement("tr")
    const titulo_1 =  document.createElement("th")
    const titulo_2 = document.createElement("th")
    titulo_1.append("Anime")
    titulo_2.append("Puntuacion")
    columna_1.appendChild(titulo_1)
    columna_2.appendChild(titulo_2)



  })
  .catch(error => {
    console.error('Error en la petición:', error);
  });
});


