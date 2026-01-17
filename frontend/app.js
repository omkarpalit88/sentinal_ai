// SentinAL Frontend Logic

let selectedFile = null;
let currentMemo = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    // Click to upload
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });
});

function handleFileSelect(file) {
    // Validate file type
    const validExtensions = ['.sql', '.tf', '.yaml', '.yml'];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();

    if (!validExtensions.includes(fileExt)) {
        showError('Invalid file type. Please upload a .sql, .tf, or .yaml file.');
        return;
    }

    selectedFile = file;

    // Show selected file
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('selectedFile').style.display = 'flex';
    document.getElementById('analyzeBtn').disabled = false;

    // Hide upload area
    document.getElementById('uploadArea').style.display = 'none';

    // Hide previous results
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('error').style.display = 'none';
}

function removeFile() {
    selectedFile = null;
    document.getElementById('selectedFile').style.display = 'none';
    document.getElementById('uploadArea').style.display = 'block';
    document.getElementById('analyzeBtn').disabled = true;
    document.getElementById('resultsSection').style.display = 'none';
}

async function analyzeFile() {
    if (!selectedFile) return;

    // Show loading
    document.getElementById('loading').style.display = 'block';
    document.getElementById('error').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'none';

    // Create form data
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        // Call API
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Analysis failed');
        }

        const result = await response.json();

        // Hide loading
        document.getElementById('loading').style.display = 'none';

        // Display results
        displayResults(result);

    } catch (error) {
        document.getElementById('loading').style.display = 'none';
        showError(error.message);
    }
}

function displayResults(result) {
    // Update risk score
    document.getElementById('riskScore').textContent = `${result.risk_score}/100`;

    // Update risk badge
    const badge = document.getElementById('riskBadge');
    badge.textContent = result.risk_classification;
    badge.className = 'risk-badge ' + result.risk_classification;

    // Update findings counts
    document.getElementById('criticalCount').textContent = result.critical_count;
    document.getElementById('highCount').textContent = result.high_count;
    document.getElementById('mediumCount').textContent = result.medium_count;
    document.getElementById('lowCount').textContent = result.low_count;

    // Update analysis metadata
    document.getElementById('cost').textContent = result.analysis_cost_usd.toFixed(6);
    document.getElementById('time').textContent = result.analysis_time_seconds.toFixed(2);

    // Render defense memo (markdown)
    const memoHtml = marked.parse(result.defense_memo);
    document.getElementById('memoContent').innerHTML = memoHtml;

    // Store memo for download
    currentMemo = result.defense_memo;

    // Show results
    document.getElementById('resultsSection').style.display = 'block';

    // Scroll to results
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

function showError(message) {
    const errorEl = document.getElementById('error');
    errorEl.textContent = message;
    errorEl.style.display = 'block';
}

function downloadMemo() {
    if (!currentMemo) return;

    // Create blob
    const blob = new Blob([currentMemo], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);

    // Create download link
    const a = document.createElement('a');
    a.href = url;
    a.download = `defense-memo-${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
