document.getElementById('formulario').addEventListener('submit', function(event) {
    event.preventDefault()

    const form = new FormData(this);
    const anime = form.get("anime")
    const puntuacion = form.get("puntuacion")
    const data = {};
    data[anime] = parseFloat(puntuacion);

  fetch('http://localhost:5000/obtener-recomendaciones', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  })
  .then(response => response.json())
  .then(result => {
    const tabla = document.createElement("table");
    const cabezera = document.createElement("thead");
    const filas = document.createElement("tr");
    const titulo_1 =  document.createElement("th");
    const titulo_2 = document.createElement("th");
    titulo_1.append("Anime");
    titulo_2.append("Puntuacion");
    filas.appendChild(titulo_1);
    filas.appendChild(titulo_2);
    cabezera.appendChild(filas);
    tabla.appendChild(cabezera);
    const contenido = document.createElement("tbody");
    
    result.forEach(element => {
        const fila = document.createElement("tr");
        const columna = document.createElement("td");
        const columna_2 = document.createElement("td");
        columna.textContent = element.title;
        columna_2.textContent = element.score;
        fila.appendChild(columna);
        fila.appendChild(columna_2);
        contenido.appendChild(fila);
    });
    tabla.appendChild(contenido);
    document.getElementById("main").appendChild(tabla);
 })
  .catch(error => {
    console.error('Error en la petición:', error);
  });
});


