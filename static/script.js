document.getElementById('ad-form').addEventListener('submit', async function(event) {
    event.preventDefault();

    const description = document.getElementById('ad-description').value;
    const resultDiv = document.getElementById('result');

    resultDiv.innerHTML = 'Creating ad...';

    try {
        const response = await fetch('/api/create-ad', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ description: description })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        resultDiv.innerHTML = `
            <h3>Ad Created (Mock)</h3>
            <p><strong>Target Audience:</strong> ${data.target_audience}</p>
            <p><strong>Budget:</strong> ${data.budget}</p>
            <p><strong>Ad Copy:</strong></p>
            <pre>${data.ad_copy}</pre>
        `;

    } catch (error) {
        resultDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
    }
});
