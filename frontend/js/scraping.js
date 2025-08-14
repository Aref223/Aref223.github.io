// Scraping Module
const scrapingModule = {
    currentPage: 1,
    currentFilters: {},
    searchTerm: '',

    async loadScrapingJobs(page = 1, filters = {}) {
        try {
            app.showLoading('Loading scraping jobs...');
            
            this.currentPage = page;
            this.currentFilters = { ...filters };
            
            const params = {
                page: page,
                limit: 10,
                ...filters
            };

            const response = await scrapingAPI.getJobs(params);
            this.displayJobs(response.items || [], response.total || 0, response.page || 1, response.pages || 1);
            
            app.hideLoading();
        } catch (error) {
            app.hideLoading();
            app.showAlert('Failed to load scraping jobs', 'danger');
            console.error('Scraping jobs load error:', error);
        }
    },

    displayJobs(jobs, total, currentPage, totalPages) {
        const container = document.getElementById('scrapingJobsList');
        if (!container) return;

        if (jobs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-briefcase"></i>
                    <h4>No scraping jobs found</h4>
                    <p>Create your first scraping job to get started.</p>
                    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#createScrapingJobModal">
                        <i class="bi bi-plus-circle me-2"></i>Create Job
                    </button>
                </div>
            `;
            return;
        }

        const jobsHtml = jobs.map(job => this.createJobCard(job)).join('');
        container.innerHTML = jobsHtml;

        // Update pagination
        this.updatePagination(currentPage, totalPages, total);
    },

    createJobCard(job) {
        const statusClass = this.getStatusClass(job.status);
        const statusIcon = this.getStatusIcon(job.status);
        
        return `
            <div class="card mb-3 job-card" data-job-id="${job.id}">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <div class="d-flex align-items-center mb-2">
                                <h5 class="card-title mb-0 me-3">${job.name}</h5>
                                <span class="badge ${statusClass}">${job.status}</span>
                            </div>
                            <p class="card-text text-muted mb-2">
                                <i class="bi bi-link-45deg me-1"></i>
                                ${job.urls?.length || 0} URLs configured
                            </p>
                            <p class="card-text text-muted mb-2">
                                <i class="bi bi-clock me-1"></i>
                                Created: ${app.formatDate(job.created_at)}
                            </p>
                            ${job.started_at ? `
                                <p class="card-text text-muted mb-2">
                                    <i class="bi bi-play-circle me-1"></i>
                                    Started: ${app.formatDate(job.started_at)}
                                </p>
                            ` : ''}
                            ${job.completed_at ? `
                                <p class="card-text text-muted mb-2">
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
            'cancelled': 'status-cancelled'
        };
        return statusClasses[status.toLowerCase()] || 'status-pending';
    },

    getStatusIcon(status) {
        const statusIcons = {
            'pending': 'bi-clock',
            'running': 'bi-play-circle',
            'completed': 'bi-check-circle',
            'failed': 'bi-x-circle',
            'cancelled': 'bi-stop-circle'
        };
        return statusIcons[status.toLowerCase()] || 'bi-clock';
    },

    getActionButtons(job) {
        const buttons = [];

        if (job.status === 'pending') {
            buttons.push(`
                <button class="btn btn-success btn-sm mb-1" onclick="scrapingModule.startJob('${job.id}')">
                    <i class="bi bi-play me-1"></i>Start
                </button>
            `);
        }

        if (job.status === 'running') {
            buttons.push(`
                <button class="btn btn-warning btn-sm mb-1" onclick="scrapingModule.cancelJob('${job.id}')">
                    <i class="bi bi-stop me-1"></i>Cancel
                </button>
            `);
        }

        if (job.status === 'failed') {
            buttons.push(`
                <button class="btn btn-info btn-sm mb-1" onclick="scrapingModule.retryJob('${job.id}')">
                    <i class="bi bi-arrow-clockwise me-1"></i>Retry
                </button>
            `);
        }

        buttons.push(`
            <button class="btn btn-outline-primary btn-sm mb-1" onclick="scrapingModule.viewJobDetails('${job.id}')">
                <i class="bi bi-eye me-1"></i>View
            </button>
        `);

        if (['completed', 'failed', 'cancelled'].includes(job.status)) {
            buttons.push(`
                <button class="btn btn-outline-danger btn-sm mb-1" onclick="scrapingModule.deleteJob('${job.id}')">
                    <i class="bi bi-trash me-1"></i>Delete
                </button>
            `);
        }

        return buttons.join('');
    },

    async startJob(jobId) {
        try {
            app.showLoading('Starting job...');
            await scrapingAPI.startJob(jobId);
            app.hideLoading();
            app.showAlert('Job started successfully', 'success');
            this.loadScrapingJobs(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to start job', 'danger');
        }
    },

    async cancelJob(jobId) {
        if (!confirm('Are you sure you want to cancel this job?')) return;

        try {
            app.showLoading('Cancelling job...');
            await scrapingAPI.cancelJob(jobId);
            app.hideLoading();
            app.showAlert('Job cancelled successfully', 'success');
            this.loadScrapingJobs(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to cancel job', 'danger');
        }
    },

    async retryJob(jobId) {
        try {
            app.showLoading('Retrying job...');
            await scrapingAPI.retryJob(jobId);
            app.hideLoading();
            app.showAlert('Job retry initiated successfully', 'success');
            this.loadScrapingJobs(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to retry job', 'danger');
        }
    },

    async deleteJob(jobId) {
        if (!confirm('Are you sure you want to delete this job? This action cannot be undone.')) return;

        try {
            app.showLoading('Deleting job...');
            await scrapingAPI.deleteJob(jobId);
            app.hideLoading();
            app.showAlert('Job deleted successfully', 'success');
            this.loadScrapingJobs(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to delete job', 'danger');
        }
    },

    async viewJobDetails(jobId) {
        try {
            app.showLoading('Loading job details...');
            const job = await scrapingAPI.getJob(jobId);
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
                        <tr><td><strong>Status:</strong></td><td><span class="badge ${this.getStatusClass(job.status)}">${job.status}</span></td></tr>
                        <tr><td><strong>Type:</strong></td><td>${job.job_type || 'N/A'}</td></tr>
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
                        <tr><td><strong>URLs:</strong></td><td>${job.urls?.length || 0}</td></tr>
                    </table>
                </div>
            </div>
            ${job.urls && job.urls.length > 0 ? `
                <div class="mt-3">
                    <h6>URLs</h6>
                    <div class="list-group">
                        ${job.urls.map(url => `
                            <div class="list-group-item">
                                <i class="bi bi-link-45deg me-2"></i>
                                <a href="${url}" target="_blank" class="text-decoration-none">${url}</a>
                            </div>
                        `).join('')}
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
                                    <th>Card Number</th>
                                    <th>Bank</th>
                                    <th>Type</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${job.results.map(result => `
                                    <tr>
                                        <td>****${result.card_number?.slice(-4) || 'N/A'}</td>
                                        <td>${result.bank_name || 'N/A'}</td>
                                        <td>${result.card_type || 'N/A'}</td>
                                        <td><span class="badge bg-${result.is_valid ? 'success' : 'danger'}">${result.is_valid ? 'Valid' : 'Invalid'}</span></td>
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
        const paginationContainer = document.getElementById('scrapingPagination');
        if (!paginationContainer) return;

        if (totalPages <= 1) {
            paginationContainer.innerHTML = '';
            return;
        }

        let paginationHtml = `
            <nav aria-label="Scraping jobs pagination">
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
        this.loadScrapingJobs(1, { search: searchTerm });
    },

    applyFilters(filters) {
        this.currentFilters = { ...filters };
        this.currentPage = 1;
        this.loadScrapingJobs(1, this.currentFilters);
    },

    loadPage(pageNumber) {
        this.loadScrapingJobs(pageNumber, this.currentFilters);
    },

    refreshJobs() {
        this.loadScrapingJobs(this.currentPage, this.currentFilters);
    }
};

// Export for global use
window.scrapingModule = scrapingModule;