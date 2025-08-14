document.getElementById('ad-form').addEventListener('submit', async function(event) {
    event.preventDefault();

    const description = document.getElementById('ad-description').value;
    const resultDiv = document.getElementById('result');

    resultDiv.innerHTML = 'Thinking... and creating ad on Facebook (mock)...';

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
        const ai_result = data.ai_result;
        const fb_result = data.facebook_result;

        resultDiv.innerHTML = `
            <h3>AI Analysis Complete:</h3>
            <p><strong>Target Audience:</strong> ${ai_result.target_audience}</p>
            <p><strong>Budget:</strong> ${ai_result.budget}</p>
            <p><strong>Ad Copy:</strong></p>
            <pre>${ai_result.ad_copy}</pre>
            <hr>
            <h3>Facebook Integration (Mock):</h3>
            <p><strong>Status:</strong> ${fb_result.success ? 'Success' : 'Failed'}</p>
            <p><strong>Message:</strong> ${fb_result.message}</p>
            <p><strong>Mock Campaign ID:</strong> ${fb_result.mock_campaign_id}</p>
        `;

    } catch (error) {
        resultDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
    }
});
