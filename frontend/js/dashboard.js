// Dashboard Module
const dashboardModule = {
    charts: {},

    async loadDashboard() {
        try {
            app.showLoading('Loading dashboard...');
            
            // Load all dashboard data in parallel
            const [userStats, scrapingStats, validationStats, cardStats, jobStats] = await Promise.all([
                usersAPI.getUserStats(),
                scrapingAPI.getScrapingStats(),
                validationAPI.getValidationStats(),
                cardsAPI.getCardStats(),
                jobsAPI.getJobStats()
            ]);

            this.updateStatsCards(userStats, scrapingStats, validationStats, cardStats, jobStats);
            this.createCharts(userStats, scrapingStats, validationStats, cardStats, jobStats);
            this.loadRecentActivity();
            
            app.hideLoading();
        } catch (error) {
            app.hideLoading();
            app.showAlert('Failed to load dashboard data', 'danger');
            console.error('Dashboard load error:', error);
        }
    },

    updateStatsCards(userStats, scrapingStats, validationStats, cardStats, jobStats) {
        // Update stats cards with data
        const statsCards = {
            'totalUsers': {
                number: userStats.total_users || 0,
                label: 'Total Users',
                icon: 'bi-people-fill',
                color: 'primary'
            },
            'activeUsers': {
                number: userStats.active_users || 0,
                label: 'Active Users',
                icon: 'bi-person-check-fill',
                color: 'success'
            },
            'totalJobs': {
                number: jobStats.total_jobs || 0,
                label: 'Total Jobs',
                icon: 'bi-briefcase-fill',
                color: 'info'
            },
            'runningJobs': {
                number: jobStats.running_jobs || 0,
                label: 'Running Jobs',
                icon: 'bi-play-circle-fill',
                color: 'warning'
            },
            'totalCards': {
                number: cardStats.total_cards || 0,
                label: 'Total Cards',
                icon: 'bi-credit-card-fill',
                color: 'primary'
            },
            'validCards': {
                number: cardStats.valid_cards || 0,
                label: 'Valid Cards',
                icon: 'bi-check-circle-fill',
                color: 'success'
            },
            'totalValidations': {
                number: validationStats.total_validations || 0,
                label: 'Total Validations',
                icon: 'bi-shield-check-fill',
                color: 'info'
            },
            'successfulValidations': {
                number: validationStats.successful_validations || 0,
                label: 'Successful Validations',
                icon: 'bi-check2-all',
                color: 'success'
            }
        };

        // Update each stats card
        Object.keys(statsCards).forEach(cardId => {
            const card = document.getElementById(cardId);
            if (card) {
                const data = statsCards[cardId];
                card.innerHTML = `
                    <div class="stats-card ${data.color}">
                        <div class="stats-icon">
                            <i class="bi ${data.icon}"></i>
                        </div>
                        <div class="stats-number">${app.formatNumber(data.number)}</div>
                        <div class="stats-label">${data.label}</div>
                    </div>
                `;
            }
        });
    },

    createCharts(userStats, scrapingStats, validationStats, cardStats, jobStats) {
        this.createUserActivityChart(userStats);
        this.createJobStatusChart(jobStats);
        this.createValidationTrendChart(validationStats);
        this.createCardTypeChart(cardStats);
    },

    createUserActivityChart(userStats) {
        const ctx = document.getElementById('userActivityChart');
        if (!ctx) return;

        // Destroy existing chart if it exists
        if (this.charts.userActivity) {
            this.charts.userActivity.destroy();
        }

        const data = userStats.activity_data || [];
        const labels = data.map(item => item.date);
        const values = data.map(item => item.count);

        this.charts.userActivity = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'User Activity',
                    data: values,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    },

    createJobStatusChart(jobStats) {
        const ctx = document.getElementById('jobStatusChart');
        if (!ctx) return;

        if (this.charts.jobStatus) {
            this.charts.jobStatus.destroy();
        }

        const statusData = jobStats.status_distribution || {};
        const labels = Object.keys(statusData);
        const values = Object.values(statusData);
        const colors = ['#198754', '#ffc107', '#dc3545', '#6c757d', '#0dcaf0'];

        this.charts.jobStatus = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    },

    createValidationTrendChart(validationStats) {
        const ctx = document.getElementById('validationTrendChart');
        if (!ctx) return;

        if (this.charts.validationTrend) {
            this.charts.validationTrend.destroy();
        }

        const data = validationStats.trend_data || [];
        const labels = data.map(item => item.date);
        const successValues = data.map(item => item.successful);
        const failedValues = data.map(item => item.failed);

        this.charts.validationTrend = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Successful',
                    data: successValues,
                    backgroundColor: '#198754',
                    borderColor: '#198754',
                    borderWidth: 1
                }, {
                    label: 'Failed',
                    data: failedValues,
                    backgroundColor: '#dc3545',
                    borderColor: '#dc3545',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    },

    createCardTypeChart(cardStats) {
        const ctx = document.getElementById('cardTypeChart');
        if (!ctx) return;

        if (this.charts.cardType) {
            this.charts.cardType.destroy();
        }

        const typeData = cardStats.type_distribution || {};
        const labels = Object.keys(typeData);
        const values = Object.values(typeData);
        const colors = ['#0d6efd', '#198754', '#ffc107', '#dc3545', '#6c757d'];

        this.charts.cardType = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    },

    async loadRecentActivity() {
        try {
            // Load recent activity from multiple sources
            const [recentJobs, recentValidations, recentCards] = await Promise.all([
                scrapingAPI.getJobs({ limit: 5, sort: '-created_at' }),
                validationAPI.getValidationHistory({ limit: 5, sort: '-created_at' }),
                cardsAPI.getCards({ limit: 5, sort: '-created_at' })
            ]);

            this.updateRecentJobs(recentJobs.items || []);
            this.updateRecentValidations(recentValidations.items || []);
            this.updateRecentCards(recentCards.items || []);
        } catch (error) {
            console.error('Failed to load recent activity:', error);
        }
    },

    updateRecentJobs(jobs) {
        const container = document.getElementById('recentJobs');
        if (!container) return;

        if (jobs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-briefcase"></i>
                    <h4>No recent jobs</h4>
                    <p>No scraping jobs have been created yet.</p>
                </div>
            `;
            return;
        }

        const jobsHtml = jobs.map(job => `
            <div class="d-flex align-items-center p-3 border-bottom">
                <div class="flex-shrink-0">
                    <i class="bi bi-briefcase text-primary fs-4"></i>
                </div>
                <div class="flex-grow-1 ms-3">
                    <h6 class="mb-1">${job.name}</h6>
                    <p class="mb-1 text-muted small">${app.truncateText(job.urls?.join(', ') || 'No URLs', 50)}</p>
                    <small class="text-muted">${app.formatDate(job.created_at)}</small>
                </div>
                <div class="flex-shrink-0">
                    <span class="badge status-${job.status.toLowerCase()}">${job.status}</span>
                </div>
            </div>
        `).join('');

        container.innerHTML = jobsHtml;
    },

    updateRecentValidations(validations) {
        const container = document.getElementById('recentValidations');
        if (!container) return;

        if (validations.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-shield-check"></i>
                    <h4>No recent validations</h4>
                    <p>No card validations have been performed yet.</p>
                </div>
            `;
            return;
        }

        const validationsHtml = validations.map(validation => `
            <div class="d-flex align-items-center p-3 border-bottom">
                <div class="flex-shrink-0">
                    <i class="bi bi-shield-check text-${validation.is_valid ? 'success' : 'danger'} fs-4"></i>
                </div>
                <div class="flex-grow-1 ms-3">
                    <h6 class="mb-1">${validation.card_number ? `****${validation.card_number.slice(-4)}` : 'Unknown Card'}</h6>
                    <p class="mb-1 text-muted small">${validation.bank_name || 'Unknown Bank'} - ${validation.card_type || 'Unknown Type'}</p>
                    <small class="text-muted">${app.formatDate(validation.created_at)}</small>
                </div>
                <div class="flex-shrink-0">
                    <span class="badge bg-${validation.is_valid ? 'success' : 'danger'}">${validation.is_valid ? 'Valid' : 'Invalid'}</span>
                </div>
            </div>
        `).join('');

        container.innerHTML = validationsHtml;
    },

    updateRecentCards(cards) {
        const container = document.getElementById('recentCards');
        if (!container) return;

        if (cards.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-credit-card"></i>
                    <h4>No recent cards</h4>
                    <p>No cards have been added yet.</p>
                </div>
            `;
            return;
        }

        const cardsHtml = cards.map(card => `
            <div class="d-flex align-items-center p-3 border-bottom">
                <div class="flex-shrink-0">
                    <i class="bi bi-credit-card text-primary fs-4"></i>
                </div>
                <div class="flex-grow-1 ms-3">
                    <h6 class="mb-1">${card.cardholder_name || 'Unknown'}</h6>
                    <p class="mb-1 text-muted small">${card.bank_name || 'Unknown Bank'} - ${card.card_type || 'Unknown Type'}</p>
                    <small class="text-muted">${app.formatDate(card.created_at)}</small>
                </div>
                <div class="flex-shrink-0">
                    <span class="badge bg-${card.is_valid ? 'success' : 'warning'}">${card.is_valid ? 'Valid' : 'Pending'}</span>
                </div>
            </div>
        `).join('');

        container.innerHTML = cardsHtml;
    },

    refreshDashboard() {
        this.loadDashboard();
    },

    destroyCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};
    }
};

// Export for global use
window.dashboardModule = dashboardModule;