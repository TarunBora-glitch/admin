
    // Reset status
    setTimeout(() => {
        statusText.innerText = 'Status:';
    }, 2000);
});

document.addEventListener('DOMContentLoaded', () => {
    const branchSelect = document.getElementById('branchSelect');
    const semesterSelect = document.getElementById('semesterSelect');
    const subjectSelect = document.getElementById('subjectSelect');

    // Fetch branches
    fetch('/api/branches')
        .then(res => res.json())
        .then(data => {
            data.forEach(branch => {
                const option = document.createElement('option');
                option.value = branch;
                option.textContent = branch;
                branchSelect.appendChild(option);
            });
        });

    // Fetch semesters
    fetch('/api/semesters')
        .then(res => res.json())
        .then(data => {
            data.forEach(sem => {
                const option = document.createElement('option');
                option.value = sem;
                option.textContent = sem;
                semesterSelect.appendChild(option);
            });
        });

    // Fetch subjects when branch & semester are selected
    function loadSubjects() {
        const branch = branchSelect.value;
        const semester = semesterSelect.value;
        if (branch && semester) {
            fetch(`/api/subjects?branch=${encodeURIComponent(branch)}&semester=${encodeURIComponent(semester)}`)
                .then(res => res.json())
                .then(data => {
                    subjectSelect.innerHTML = '<option value="">-- Select Subject --</option>';
                    data.forEach(subject => {
                        const option = document.createElement('option');
                        option.value = subject;
                        option.textContent = subject;
                        subjectSelect.appendChild(option);
                    });
                });
        }
    }

    branchSelect.addEventListener('change', loadSubjects);
    semesterSelect.addEventListener('change', loadSubjects);
});
