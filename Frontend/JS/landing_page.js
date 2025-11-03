function toggleForm() {
        document.querySelectorAll('.form-container').forEach(el => el.classList.toggle('hidden'));
}

document.getElementById('registro').addEventListener('submit', function(event) {
  event.preventDefault(); 

  const form = event.target;  
  const formData = new FormData(form);

  const data = Object.fromEntries(formData.entries());

  fetch('http://localhost:5000/register', {
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
    alert(result);
  })
  .catch(error => {
    console.error('Error:', error);
  });
});

document.getElementById('inicio').addEventListener('submit', function(event) {
    event.preventDefault()

    const form = event.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

  fetch('http://localhost:5000/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })
  .then(response => response.text())
  .then(result => {
    document.open();
    document.write(result)
    document.close();
  })
  .catch(error => {
    console.error('Error en la petición:', error);
  })
});


