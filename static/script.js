document.getElementById('planForm').addEventListener('submit', function (e) {
    e.preventDefault();

    const courses = document.getElementById('courses').value.replace(/\s+/g, '');
    const semester = document.getElementById('semester').value.replace(/\s+/g, '');
    const resultDiv = document.getElementById('result');

    fetch(`/create?courses=${courses}&semester=${semester}`)
        .then(async response => {
            if (response.ok) {
                return response.json();
            } else if (response.status === 429) {
                throw new Error("HTTP 429 Too Many Requests");
            }
            else {
                const err = await response.json();
                throw new Error(err.detail || `HTTP ${response.status}`);
            }
        })
        .then(data => {
            resultDiv.innerHTML = `<strong>${data.url}</strong></br></br>${data.courses.join('\n')}`;
            resultDiv.className = 'success';
        })
        .catch(error => {
            resultDiv.textContent = `${error.message}`;
            resultDiv.className = 'error';
        });
});
