const tickerForm = document.querySelector("#ticker-form");
const tickerInput = document.querySelector("#ticker-input");
const responseDiv = document.querySelector("#response");

tickerForm.addEventListener("submit", (event) => {
  event.preventDefault();

  const ticker = tickerInput.value;

  fetch(`http://localhost:3000/stock-info?ticker=${ticker}`)
    .then(response => response.json())
    .then(data => {
      responseDiv.innerHTML = `
        <p>Stock Name: ${data.name}</p>
        <p>Current Price: ${data.price}</p>
      `;
    })
    .catch(error => console.error(error));
});
