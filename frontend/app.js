// API Configuration
const API_BASE_URL = ''; // Use relative URL for Docker deployment
const POLL_INTERVAL = 5000; // 5 seconds

// State
let currentJobs = [];
let pollInterval = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initHealthCheck();
    initUrlForm();
    initFileForm();
    initJobsList();
    initSettings();
    loadLanguages();
});

// ==================== Tab Management ====================
function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.getAttribute('data-tab');

            // Update buttons
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            // Update content
            tabContents.forEach(content => content.classList.remove('active'));
            document.getElementById(`${targetTab}-tab`).classList.add('active');

            // Load jobs when switching to list tab
            if (targetTab === 'list') {
                loadJobs();
            }
        });
    });
}

// ==================== Health Check ====================
function initHealthCheck() {
    checkHealth();
    setInterval(checkHealth, 10000); // Check every 10 seconds
}

async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();

        const indicator = document.getElementById('health-indicator');
        const text = document.getElementById('health-text');

        if (data.status === 'healthy') {
            indicator.className = 'status-dot healthy';
            text.textContent = 'Healthy';
        } else {
            indicator.className = 'status-dot unhealthy';
            text.textContent = 'Unhealthy';
        }
    } catch (error) {
        const indicator = document.getElementById('health-indicator');
        const text = document.getElementById('health-text');
        indicator.className = 'status-dot unhealthy';
        text.textContent = 'Connection Failed';
    }
}

// ==================== URL Form ====================
function initUrlForm() {
    const inputTypes = document.querySelectorAll('input[name="input-type"]');
    const urlForm = document.getElementById('url-form');
    const fileForm = document.getElementById('file-form');
    const enableTranslation = document.getElementById('enable-translation');
    const translationOptions = document.getElementById('translation-options');

    // Toggle between URL and file input
    inputTypes.forEach(input => {
        input.addEventListener('change', (e) => {
            if (e.target.value === 'url') {
                urlForm.style.display = 'block';
                fileForm.style.display = 'none';
            } else {
                urlForm.style.display = 'none';
                fileForm.style.display = 'block';
            }
        });
    });

    // Toggle translation options
    enableTranslation.addEventListener('change', (e) => {
        translationOptions.style.display = e.target.checked ? 'block' : 'none';
    });

    // Handle form submission
    urlForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await createJobFromUrl();
    });
}

async function createJobFromUrl() {
    const url = document.getElementById('url-input').value;
    const format = document.getElementById('subtitle-format').value;
    const enableTranslation = document.getElementById('enable-translation').checked;
    const targetLanguage = enableTranslation ? document.getElementById('target-language').value : null;

    const button = document.getElementById('create-url-job');
    button.disabled = true;
    button.textContent = 'Creating Job...';

    try {
        const payload = {
            url: url,
            subtitle_format: format
        };

        if (enableTranslation && targetLanguage) {
            payload.translate = true;
            payload.target_language = targetLanguage;
        }

        const response = await fetch(`${API_BASE_URL}/api/v1/jobs`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error('Failed to create job');
        }

        const data = await response.json();
        showToast('Job created successfully', 'success');

        // Reset form
        document.getElementById('url-input').value = '';

        // Switch to jobs list tab
        document.querySelector('[data-tab="list"]').click();

    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        button.disabled = false;
        button.textContent = 'Create Job';
    }
}

// ==================== File Upload ====================
function initFileForm() {
    const dropZone = document.getElementById('file-drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileNameDisplay = document.getElementById('file-name');
    const fileForm = document.getElementById('file-form');
    const enableTranslation = document.getElementById('file-enable-translation');
    const translationOptions = document.getElementById('file-translation-options');

    // Click to select file
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            fileNameDisplay.textContent = `Selected file: ${file.name}`;
        }
    });

    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');

        const file = e.dataTransfer.files[0];
        if (file) {
            fileInput.files = e.dataTransfer.files;
            fileNameDisplay.textContent = `Selected file: ${file.name}`;
        }
    });

    // Toggle translation options
    enableTranslation.addEventListener('change', (e) => {
        translationOptions.style.display = e.target.checked ? 'block' : 'none';
    });

    // Handle form submission
    fileForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await uploadFile();
    });
}

async function uploadFile() {
    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];

    if (!file) {
        showToast('Please select a file', 'error');
        return;
    }

    const format = document.getElementById('file-subtitle-format').value;
    const enableTranslation = document.getElementById('file-enable-translation').checked;
    const targetLanguage = enableTranslation ? document.getElementById('file-target-language').value : null;

    const button = document.getElementById('create-file-job');
    const progressContainer = document.getElementById('upload-progress');
    const progressFill = document.getElementById('upload-progress-fill');
    const progressText = document.getElementById('upload-progress-text');

    button.disabled = true;
    button.textContent = 'Uploading...';
    progressContainer.style.display = 'block';

    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('subtitle_format', format);

        if (enableTranslation && targetLanguage) {
            formData.append('translate', 'true');
            formData.append('target_language', targetLanguage);
        }

        // Use XMLHttpRequest for upload progress tracking
        await new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            // Upload progress event
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percentComplete = Math.round((e.loaded / e.total) * 100);
                    progressFill.style.width = percentComplete + '%';

                    if (percentComplete < 100) {
                        progressText.textContent = `Uploading file... ${percentComplete}%`;
                    } else {
                        progressText.textContent = 'Processing on server...';
                        button.textContent = 'Processing...';
                    }
                }
            });

            // Load event (upload complete)
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const data = JSON.parse(xhr.responseText);
                        resolve(data);
                    } catch (e) {
                        reject(new Error('Failed to parse response'));
                    }
                } else {
                    reject(new Error('File upload failed'));
                }
            });

            // Error event
            xhr.addEventListener('error', () => {
                reject(new Error('Network error'));
            });

            // Abort event
            xhr.addEventListener('abort', () => {
                reject(new Error('Upload cancelled'));
            });

            xhr.open('POST', `${API_BASE_URL}/api/v1/jobs/upload`);
            xhr.send(formData);
        });

        showToast('File uploaded successfully', 'success');

        // Reset form
        fileInput.value = '';
        document.getElementById('file-name').textContent = '';
        progressContainer.style.display = 'none';
        progressFill.style.width = '0%';
        progressText.textContent = 'Uploading file... 0%';

        // Switch to jobs list tab
        document.querySelector('[data-tab="list"]').click();

    } catch (error) {
        showToast(error.message, 'error');
        progressContainer.style.display = 'none';
        progressFill.style.width = '0%';
        progressText.textContent = 'Uploading file... 0%';
    } finally {
        button.disabled = false;
        button.textContent = 'Upload and Create Job';
    }
}

// ==================== Jobs List ====================
function initJobsList() {
    const refreshButton = document.getElementById('refresh-jobs');
    refreshButton.addEventListener('click', loadJobs);

    // Start polling for jobs
    startJobsPolling();
}

function startJobsPolling() {
    // Initial load
    loadJobs();

    // Poll every 5 seconds
    pollInterval = setInterval(() => {
        // Only poll if we're on the jobs list tab
        const listTab = document.getElementById('list-tab');
        if (listTab.classList.contains('active')) {
            loadJobs();
        }
    }, POLL_INTERVAL);
}

async function loadJobs() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/jobs`);

        if (!response.ok) {
            throw new Error('Failed to load job list');
        }

        const data = await response.json();
        currentJobs = data.jobs || [];
        renderJobs();

    } catch (error) {
        const tbody = document.getElementById('jobs-tbody');
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">Failed to load jobs</td></tr>';
    }
}

function renderJobs() {
    const tbody = document.getElementById('jobs-tbody');

    if (currentJobs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No jobs found</td></tr>';
        return;
    }

    tbody.innerHTML = currentJobs.map(job => {
        const statusClass = getStatusClass(job.status);
        const statusText = getStatusText(job.status);
        // Estimate progress if not provided by API
        const progress = job.progress !== null ? job.progress : estimateProgress(job.status);
        const jobId = job.job_id || job.id;
        const shortId = jobId.substring(0, 8) + '...';

        return `
            <tr>
                <td>${shortId}</td>
                <td>${getJobTypeText(job)}</td>
                <td><span class="status-badge status-${statusClass}">${statusText}</span></td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                    <span>${progress}%</span>
                </td>
                <td>${formatDate(job.created_at)}</td>
                <td>
                    <div class="action-buttons">
                        ${job.status === 'completed' ?
                            `<button class="btn btn-sm btn-primary" onclick="downloadJob('${jobId}')">Download</button>` :
                            ''}
                        ${job.status !== 'completed' && job.status !== 'failed' && job.status !== 'cancelled' ?
                            `<button class="btn btn-sm btn-secondary" onclick="cancelJob('${jobId}')">Cancel</button>` :
                            ''}
                        ${job.error ?
                            `<button class="btn btn-sm btn-secondary" onclick="showError('${jobId}')">Error</button>` :
                            ''}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function estimateProgress(status) {
    // Estimate progress based on status when API doesn't provide it
    const progressMap = {
        'pending': 0,
        'downloading': 20,
        'splitting': 40,
        'transcribing': 60,
        'translating': 80,
        'saving': 90,
        'completed': 100,
        'failed': 0,
        'cancelled': 0
    };
    return progressMap[status] || 0;
}

function getJobTypeText(job) {
    // Since API doesn't return input source, show job type or ID
    if (job.error) {
        return 'Error occurred';
    }
    return `Job #${(job.job_id || job.id).substring(0, 8)}`;
}

function getStatusClass(status) {
    const statusMap = {
        'pending': 'pending',
        'downloading': 'processing',
        'splitting': 'processing',
        'transcribing': 'processing',
        'translating': 'processing',
        'saving': 'processing',
        'completed': 'completed',
        'failed': 'failed',
        'cancelled': 'cancelled'
    };
    return statusMap[status] || 'pending';
}

function getStatusText(status) {
    const textMap = {
        'pending': 'Pending',
        'downloading': 'Downloading',
        'splitting': 'Splitting',
        'transcribing': 'Transcribing',
        'translating': 'Translating',
        'saving': 'Saving',
        'completed': 'Completed',
        'failed': 'Failed',
        'cancelled': 'Cancelled'
    };
    return textMap[status] || status;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

async function downloadJob(jobId) {
    try {
        window.location.href = `${API_BASE_URL}/api/v1/jobs/${jobId}/download`;
        showToast('Starting download', 'success');
    } catch (error) {
        showToast('Download failed', 'error');
    }
}

async function cancelJob(jobId) {
    if (!confirm('Are you sure you want to cancel this job?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to cancel job');
        }

        showToast('Job has been cancelled', 'success');
        loadJobs();

    } catch (error) {
        showToast(error.message, 'error');
    }
}

function showError(jobId) {
    const job = currentJobs.find(j => (j.job_id || j.id) === jobId);
    if (job && job.error) {
        alert(`Error details:\n\n${job.error}`);
    }
}

// ==================== Settings ====================
function initSettings() {
    loadSettings();

    const settingsForm = document.getElementById('settings-form');
    const resetButton = document.getElementById('reset-settings');

    settingsForm.addEventListener('submit', (e) => {
        e.preventDefault();
        saveSettings();
    });

    resetButton.addEventListener('click', () => {
        if (confirm('Are you sure you want to reset settings?')) {
            resetSettings();
        }
    });
}

function loadSettings() {
    const settings = JSON.parse(localStorage.getItem('sogon-settings')) || getDefaultSettings();

    document.getElementById('default-format').value = settings.defaultFormat;
    document.getElementById('default-translation').checked = settings.defaultTranslation;
    document.getElementById('default-language').value = settings.defaultLanguage;
    document.getElementById('whisper-model').value = settings.whisperModel;
}

function saveSettings() {
    const settings = {
        defaultFormat: document.getElementById('default-format').value,
        defaultTranslation: document.getElementById('default-translation').checked,
        defaultLanguage: document.getElementById('default-language').value,
        whisperModel: document.getElementById('whisper-model').value
    };

    localStorage.setItem('sogon-settings', JSON.stringify(settings));
    showToast('Settings saved successfully', 'success');
}

function resetSettings() {
    const settings = getDefaultSettings();
    localStorage.setItem('sogon-settings', JSON.stringify(settings));
    loadSettings();
    showToast('Settings reset successfully', 'success');
}

function getDefaultSettings() {
    return {
        defaultFormat: 'srt',
        defaultTranslation: false,
        defaultLanguage: 'ko',
        whisperModel: 'whisper-large-v3-turbo'
    };
}

// ==================== Languages ====================
async function loadLanguages() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/languages`);

        if (!response.ok) {
            throw new Error('Failed to load language list');
        }

        const data = await response.json();
        populateLanguageSelects(data.languages);

    } catch (error) {
        console.error('Failed to load languages:', error);
        // Use fallback languages
        const fallbackLanguages = {
            'ko': 'Korean',
            'en': 'English',
            'ja': '日本語',
            'zh': '中文',
            'es': 'Español',
            'fr': 'Français',
            'de': 'Deutsch'
        };
        populateLanguageSelects(fallbackLanguages);
    }
}

function populateLanguageSelects(languages) {
    const selects = [
        document.getElementById('target-language'),
        document.getElementById('file-target-language'),
        document.getElementById('default-language')
    ];

    selects.forEach(select => {
        select.innerHTML = '';
        Object.entries(languages).forEach(([code, name]) => {
            const option = document.createElement('option');
            option.value = code;
            option.textContent = name;
            select.appendChild(option);
        });
    });
}

// ==================== Toast Notifications ====================
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast show ${type}`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}
