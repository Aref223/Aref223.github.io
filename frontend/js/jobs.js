// Jobs Module
const jobsModule = {
    currentPage: 1,
    currentFilters: {},
    searchTerm: '',

    async loadJobs(page = 1, filters = {}) {
        try {
            app.showLoading('Loading jobs...');
            
            this.currentPage = page;
            this.currentFilters = { ...filters };
            
            const params = {
                page: page,
                limit: 10,
                ...filters
            };

            const response = await jobsAPI.getJobs(params);
            this.displayJobs(response.items || [], response.total || 0, response.page || 1, response.pages || 1);
            
            app.hideLoading();
        } catch (error) {
            app.hideLoading();
            app.showAlert('Failed to load jobs', 'danger');
            console.error('Jobs load error:', error);
        }
    },

    displayJobs(jobs, total, currentPage, totalPages) {
        const container = document.getElementById('jobsList');
        if (!container) return;

        if (jobs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-briefcase"></i>
                    <h4>No jobs found</h4>
                    <p>No jobs have been created yet.</p>
                </div>
            `;
            return;
        }

        const jobsHtml = jobs.map(job => this.createJobItem(job)).join('');
        container.innerHTML = jobsHtml;

        // Update pagination
        this.updatePagination(currentPage, totalPages, total);
    },

    createJobItem(job) {
        const statusClass = this.getStatusClass(job.status);
        const statusIcon = this.getStatusIcon(job.status);
        const jobTypeIcon = this.getJobTypeIcon(job.job_type);
        
        return `
            <div class="card mb-3 job-item" data-job-id="${job.id}">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <div class="d-flex align-items-center mb-2">
                                <h6 class="card-title mb-0 me-3">
                                    <i class="bi ${jobTypeIcon} me-2"></i>
                                    ${job.name}
                                </h6>
                                <span class="badge ${statusClass}">${job.status}</span>
                            </div>
                            <p class="card-text text-muted mb-1">
                                <i class="bi bi-tag me-1"></i>
                                Type: ${job.job_type || 'Unknown'}
                            </p>
                            <p class="card-text text-muted mb-1">
                                <i class="bi bi-clock me-1"></i>
                                Created: ${app.formatDate(job.created_at)}
                            </p>
                            ${job.started_at ? `
                                <p class="card-text text-muted mb-1">
                                    <i class="bi bi-play-circle me-1"></i>
                                    Started: ${app.formatDate(job.started_at)}
                                </p>
                            ` : ''}
                            ${job.completed_at ? `
                                <p class="card-text text-muted mb-1">
                                    <i class="bi bi-check-circle me-1"></i>
                                    Completed: ${app.formatDate(job.completed_at)}
                                </p>
                            ` : ''}
                            ${job.progress ? `
                                <div class="progress mb-2" style="height: 6px;">
                                    <div class="progress-bar" role="progressbar" 
                                         style="width: ${job.progress}%" 
                                         aria-valuenow="${job.progress}" 
                                         aria-valuemin="0" 
                                         aria-valuemax="100">
                                    </div>
                                </div>
                                <small class="text-muted">${job.progress}% complete</small>
                            ` : ''}
                            ${job.error_message ? `
                                <div class="alert alert-danger alert-sm mt-2">
                                    <i class="bi bi-exclamation-triangle me-1"></i>
                                    ${app.truncateText(job.error_message, 100)}
                                </div>
                            ` : ''}
                        </div>
                        <div class="col-md-4 text-end">
                            <div class="btn-group-vertical w-100">
                                ${this.getActionButtons(job)}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    getStatusClass(status) {
        const statusClasses = {
            'pending': 'status-pending',
            'running': 'status-running',
            'completed': 'status-completed',
            'failed': 'status-failed',
            'cancelled': 'status-cancelled',
            'paused': 'status-pending'
        };
        return statusClasses[status.toLowerCase()] || 'status-pending';
    },

    getStatusIcon(status) {
        const statusIcons = {
            'pending': 'bi-clock',
            'running': 'bi-play-circle',
            'completed': 'bi-check-circle',
            'failed': 'bi-x-circle',
            'cancelled': 'bi-stop-circle',
            'paused': 'bi-pause-circle'
        };
        return statusIcons[status.toLowerCase()] || 'bi-clock';
    },

    getJobTypeIcon(jobType) {
        const typeIcons = {
            'scraping': 'bi-globe',
            'validation': 'bi-shield-check',
            'processing': 'bi-gear',
            'export': 'bi-download',
            'import': 'bi-upload'
        };
        return typeIcons[jobType?.toLowerCase()] || 'bi-briefcase';
    },

    getActionButtons(job) {
        const buttons = [];

        if (job.status === 'pending') {
            buttons.push(`
                <button class="btn btn-success btn-sm mb-1" onclick="jobsModule.startJob('${job.id}')">
                    <i class="bi bi-play me-1"></i>Start
                </button>
            `);
        }

        if (job.status === 'running') {
            buttons.push(`
                <button class="btn btn-warning btn-sm mb-1" onclick="jobsModule.pauseJob('${job.id}')">
                    <i class="bi bi-pause me-1"></i>Pause
                </button>
            `);
        }

        if (job.status === 'paused') {
            buttons.push(`
                <button class="btn btn-success btn-sm mb-1" onclick="jobsModule.resumeJob('${job.id}')">
                    <i class="bi bi-play me-1"></i>Resume
                </button>
            `);
        }

        if (job.status === 'failed') {
            buttons.push(`
                <button class="btn btn-info btn-sm mb-1" onclick="jobsModule.retryJob('${job.id}')">
                    <i class="bi bi-arrow-clockwise me-1"></i>Retry
                </button>
            `);
        }

        buttons.push(`
            <button class="btn btn-outline-primary btn-sm mb-1" onclick="jobsModule.viewJobDetails('${job.id}')">
                <i class="bi bi-eye me-1"></i>View
            </button>
        `);

        if (['completed', 'failed', 'cancelled'].includes(job.status)) {
            buttons.push(`
                <button class="btn btn-outline-danger btn-sm mb-1" onclick="jobsModule.deleteJob('${job.id}')">
                    <i class="bi bi-trash me-1"></i>Delete
                </button>
            `);
        }

        return buttons.join('');
    },

    async startJob(jobId) {
        try {
            app.showLoading('Starting job...');
            await jobsAPI.resumeJob(jobId); // Using resume for starting
            app.hideLoading();
            app.showAlert('Job started successfully', 'success');
            this.loadJobs(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to start job', 'danger');
        }
    },

    async pauseJob(jobId) {
        try {
            app.showLoading('Pausing job...');
            await jobsAPI.pauseJob(jobId);
            app.hideLoading();
            app.showAlert('Job paused successfully', 'success');
            this.loadJobs(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to pause job', 'danger');
        }
    },

    async resumeJob(jobId) {
        try {
            app.showLoading('Resuming job...');
            await jobsAPI.resumeJob(jobId);
            app.hideLoading();
            app.showAlert('Job resumed successfully', 'success');
            this.loadJobs(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to resume job', 'danger');
        }
    },

    async retryJob(jobId) {
        try {
            app.showLoading('Retrying job...');
            await jobsAPI.retryJob(jobId);
            app.hideLoading();
            app.showAlert('Job retry initiated successfully', 'success');
            this.loadJobs(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to retry job', 'danger');
        }
    },

    async deleteJob(jobId) {
        if (!confirm('Are you sure you want to delete this job? This action cannot be undone.')) return;

        try {
            app.showLoading('Deleting job...');
            await jobsAPI.deleteJob(jobId);
            app.hideLoading();
            app.showAlert('Job deleted successfully', 'success');
            this.loadJobs(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to delete job', 'danger');
        }
    },

    async viewJobDetails(jobId) {
        try {
            app.showLoading('Loading job details...');
            const job = await jobsAPI.getJob(jobId);
            app.hideLoading();
            this.showJobDetailsModal(job);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to load job details', 'danger');
        }
    },

    showJobDetailsModal(job) {
        const modal = document.getElementById('jobDetailsModal');
        if (!modal) return;

        const modalBody = modal.querySelector('.modal-body');
        modalBody.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Job Information</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Name:</strong></td><td>${job.name}</td></tr>
                        <tr><td><strong>Type:</strong></td><td>${job.job_type || 'N/A'}</td></tr>
                        <tr><td><strong>Status:</strong></td><td><span class="badge ${this.getStatusClass(job.status)}">${job.status}</span></td></tr>
                        <tr><td><strong>Created:</strong></td><td>${app.formatDate(job.created_at)}</td></tr>
                        ${job.started_at ? `<tr><td><strong>Started:</strong></td><td>${app.formatDate(job.started_at)}</td></tr>` : ''}
                        ${job.completed_at ? `<tr><td><strong>Completed:</strong></td><td>${app.formatDate(job.completed_at)}</td></tr>` : ''}
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>Configuration</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Max Retries:</strong></td><td>${job.max_retries || 'N/A'}</td></tr>
                        <tr><td><strong>Duration Limit:</strong></td><td>${job.duration_limit || 'N/A'} minutes</td></tr>
                        <tr><td><strong>Priority:</strong></td><td>${job.priority || 'Normal'}</td></tr>
                        <tr><td><strong>Created By:</strong></td><td>${job.user?.username || 'N/A'}</td></tr>
                    </table>
                </div>
            </div>
            
            ${job.progress ? `
                <div class="mt-3">
                    <h6>Progress</h6>
                    <div class="progress mb-2">
                        <div class="progress-bar" role="progressbar" 
                             style="width: ${job.progress}%" 
                             aria-valuenow="${job.progress}" 
                             aria-valuemin="0" 
                             aria-valuemax="100">
                            ${job.progress}%
                        </div>
                    </div>
                </div>
            ` : ''}
            
            ${job.error_message ? `
                <div class="mt-3">
                    <h6>Error Details</h6>
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        ${job.error_message}
                    </div>
                </div>
            ` : ''}
            
            ${job.results && job.results.length > 0 ? `
                <div class="mt-3">
                    <h6>Results</h6>
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Item</th>
                                    <th>Status</th>
                                    <th>Details</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${job.results.map(result => `
                                    <tr>
                                        <td>${result.item || 'N/A'}</td>
                                        <td><span class="badge bg-${result.success ? 'success' : 'danger'}">${result.success ? 'Success' : 'Failed'}</span></td>
                                        <td>${result.details || 'N/A'}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            ` : ''}
        `;

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    },

    updatePagination(currentPage, totalPages, total) {
        const paginationContainer = document.getElementById('jobsPagination');
        if (!paginationContainer) return;

        if (totalPages <= 1) {
            paginationContainer.innerHTML = '';
            return;
        }

        let paginationHtml = `
            <nav aria-label="Jobs pagination">
                <ul class="pagination justify-content-center">
        `;

        // Previous button
        paginationHtml += `
            <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page-number="${currentPage - 1}">Previous</a>
            </li>
        `;

        // Page numbers
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);

        for (let i = startPage; i <= endPage; i++) {
            paginationHtml += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" data-page-number="${i}">${i}</a>
                </li>
            `;
        }

        // Next button
        paginationHtml += `
            <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page-number="${currentPage + 1}">Next</a>
            </li>
        `;

        paginationHtml += `
                </ul>
            </nav>
            <div class="text-center text-muted">
                Showing ${((currentPage - 1) * 10) + 1} to ${Math.min(currentPage * 10, total)} of ${total} jobs
            </div>
        `;

        paginationContainer.innerHTML = paginationHtml;
    },

    searchJobs(searchTerm) {
        this.searchTerm = searchTerm;
        this.currentPage = 1;
        this.loadJobs(1, { search: searchTerm });
    },

    applyFilters(filters) {
        this.currentFilters = { ...filters };
        this.currentPage = 1;
        this.loadJobs(1, this.currentFilters);
    },

    loadPage(pageNumber) {
        this.loadJobs(pageNumber, this.currentFilters);
    },

    refreshJobs() {
        this.loadJobs(this.currentPage, this.currentFilters);
    }
};

// Export for global use
window.jobsModule = jobsModule;