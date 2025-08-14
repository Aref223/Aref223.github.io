// Main Application Controller
class App {
    constructor() {
        this.currentUser = null;
        this.currentPage = 'login';
        this.pages = ['login', 'register', 'dashboard', 'scraping', 'validation', 'cards', 'jobs', 'users'];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkAuthStatus();
        this.loadPage();
    }

    setupEventListeners() {
        // Navigation event listeners
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-page]')) {
                e.preventDefault();
                const page = e.target.getAttribute('data-page');
                this.navigateTo(page);
            }

            if (e.target.matches('[data-action="logout"]')) {
                e.preventDefault();
                this.logout();
            }
        });

        // Modal event listeners
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-bs-toggle="modal"]')) {
                const modalId = e.target.getAttribute('data-bs-target');
                this.openModal(modalId);
            }
        });

        // Form submission listeners
        document.addEventListener('submit', (e) => {
            if (e.target.matches('#loginForm')) {
                e.preventDefault();
                this.handleLogin(e.target);
            }

            if (e.target.matches('#registerForm')) {
                e.preventDefault();
                this.handleRegister(e.target);
            }

            if (e.target.matches('#createScrapingJobForm')) {
                e.preventDefault();
                this.handleCreateScrapingJob(e.target);
            }

            if (e.target.matches('#addCardForm')) {
                e.preventDefault();
                this.handleAddCard(e.target);
            }

            if (e.target.matches('#addUserForm')) {
                e.preventDefault();
                this.handleAddUser(e.target);
            }
        });

        // Search and filter listeners
        document.addEventListener('input', (e) => {
            if (e.target.matches('[data-search]')) {
                this.handleSearch(e.target);
            }
        });

        // Pagination listeners
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-page-number]')) {
                e.preventDefault();
                const pageNumber = parseInt(e.target.getAttribute('data-page-number'));
                this.handlePagination(pageNumber);
            }
        });
    }

    async checkAuthStatus() {
        const token = localStorage.getItem('access_token');
        if (token) {
            try {
                const user = await authAPI.getCurrentUser();
                this.currentUser = user;
                this.updateUserInterface();
                this.navigateTo('dashboard');
            } catch (error) {
                console.error('Auth check failed:', error);
                this.logout();
            }
        } else {
            this.navigateTo('login');
        }
    }

    updateUserInterface() {
        if (this.currentUser) {
            // Update user dropdown
            const userDropdown = document.getElementById('userDropdown');
            if (userDropdown) {
                userDropdown.textContent = this.currentUser.username;
            }

            // Show/hide admin features
            const adminElements = document.querySelectorAll('[data-admin-only]');
            adminElements.forEach(element => {
                if (this.currentUser.role === 'admin') {
                    element.style.display = '';
                } else {
                    element.style.display = 'none';
                }
            });

            // Show/hide scraper features
            const scraperElements = document.querySelectorAll('[data-scraper-only]');
            scraperElements.forEach(element => {
                if (['admin', 'scraper'].includes(this.currentUser.role)) {
                    element.style.display = '';
                } else {
                    element.style.display = 'none';
                }
            });
        }
    }

    navigateTo(page) {
        if (!this.pages.includes(page)) {
            console.error('Invalid page:', page);
            return;
        }

        // Check authentication for protected pages
        if (page !== 'login' && page !== 'register' && !this.currentUser) {
            this.navigateTo('login');
            return;
        }

        this.currentPage = page;
        this.loadPage();
        this.updateNavigation();
    }

    loadPage() {
        // Hide all pages
        this.pages.forEach(page => {
            const pageElement = document.getElementById(`${page}Page`);
            if (pageElement) {
                pageElement.style.display = 'none';
            }
        });

        // Show current page
        const currentPageElement = document.getElementById(`${this.currentPage}Page`);
        if (currentPageElement) {
            currentPageElement.style.display = 'block';
            currentPageElement.classList.add('fade-in');
        }

        // Load page-specific content
        this.loadPageContent();
    }

    loadPageContent() {
        switch (this.currentPage) {
            case 'dashboard':
                dashboardModule.loadDashboard();
                break;
            case 'scraping':
                scrapingModule.loadScrapingJobs();
                break;
            case 'validation':
                validationModule.loadValidationHistory();
                break;
            case 'cards':
                cardsModule.loadCards();
                break;
            case 'jobs':
                jobsModule.loadJobs();
                break;
            case 'users':
                if (this.currentUser?.role === 'admin') {
                    usersModule.loadUsers();
                } else {
                    this.showAlert('Access denied. Admin privileges required.', 'danger');
                    this.navigateTo('dashboard');
                }
                break;
        }
    }

    updateNavigation() {
        // Update active nav link
        const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('data-page') === this.currentPage) {
                link.classList.add('active');
            }
        });
    }

    async handleLogin(form) {
        const formData = new FormData(form);
        const loginData = {
            username: formData.get('username'),
            password: formData.get('password')
        };

        try {
            this.showLoading('Logging in...');
            const response = await authAPI.login(loginData);
            
            localStorage.setItem('access_token', response.access_token);
            localStorage.setItem('refresh_token', response.refresh_token);
            
            this.currentUser = response.user;
            this.updateUserInterface();
            this.hideLoading();
            this.showAlert('Login successful!', 'success');
            this.navigateTo('dashboard');
        } catch (error) {
            this.hideLoading();
            this.showAlert(error.message || 'Login failed', 'danger');
        }
    }

    async handleRegister(form) {
        const formData = new FormData(form);
        const registerData = {
            username: formData.get('username'),
            email: formData.get('email'),
            password: formData.get('password'),
            confirm_password: formData.get('confirm_password')
        };

        if (registerData.password !== registerData.confirm_password) {
            this.showAlert('Passwords do not match', 'danger');
            return;
        }

        try {
            this.showLoading('Creating account...');
            await authAPI.register(registerData);
            this.hideLoading();
            this.showAlert('Account created successfully! Please log in.', 'success');
            this.navigateTo('login');
        } catch (error) {
            this.hideLoading();
            this.showAlert(error.message || 'Registration failed', 'danger');
        }
    }

    async handleCreateScrapingJob(form) {
        const formData = new FormData(form);
        const jobData = {
            name: formData.get('name'),
            urls: formData.get('urls').split('\n').filter(url => url.trim()),
            job_type: formData.get('job_type'),
            max_retries: parseInt(formData.get('max_retries')),
            duration_limit: parseInt(formData.get('duration_limit'))
        };

        try {
            this.showLoading('Creating scraping job...');
            await scrapingAPI.createJob(jobData);
            this.hideLoading();
            this.showAlert('Scraping job created successfully!', 'success');
            this.closeModal('createScrapingJobModal');
            form.reset();
            scrapingModule.loadScrapingJobs();
        } catch (error) {
            this.hideLoading();
            this.showAlert(error.message || 'Failed to create scraping job', 'danger');
        }
    }

    async handleAddCard(form) {
        const formData = new FormData(form);
        const cardData = {
            card_number: formData.get('card_number'),
            expiry_date: formData.get('expiry_date'),
            cvv: formData.get('cvv'),
            cardholder_name: formData.get('cardholder_name'),
            bank_name: formData.get('bank_name'),
            card_type: formData.get('card_type'),
            country: formData.get('country')
        };

        try {
            this.showLoading('Adding card...');
            await cardsAPI.createCard(cardData);
            this.hideLoading();
            this.showAlert('Card added successfully!', 'success');
            this.closeModal('addCardModal');
            form.reset();
            cardsModule.loadCards();
        } catch (error) {
            this.hideLoading();
            this.showAlert(error.message || 'Failed to add card', 'danger');
        }
    }

    async handleAddUser(form) {
        const formData = new FormData(form);
        const userData = {
            username: formData.get('username'),
            email: formData.get('email'),
            password: formData.get('password'),
            role: formData.get('role'),
            first_name: formData.get('first_name'),
            last_name: formData.get('last_name')
        };

        try {
            this.showLoading('Creating user...');
            await usersAPI.createUser(userData);
            this.hideLoading();
            this.showAlert('User created successfully!', 'success');
            this.closeModal('addUserModal');
            form.reset();
            usersModule.loadUsers();
        } catch (error) {
            this.hideLoading();
            this.showAlert(error.message || 'Failed to create user', 'danger');
        }
    }

    handleSearch(input) {
        const searchTerm = input.value.toLowerCase();
        const searchType = input.getAttribute('data-search');
        
        switch (searchType) {
            case 'scraping':
                scrapingModule.searchJobs(searchTerm);
                break;
            case 'validation':
                validationModule.searchHistory(searchTerm);
                break;
            case 'cards':
                cardsModule.searchCards(searchTerm);
                break;
            case 'jobs':
                jobsModule.searchJobs(searchTerm);
                break;
            case 'users':
                usersModule.searchUsers(searchTerm);
                break;
        }
    }

    handlePagination(pageNumber) {
        const currentModule = this.getCurrentModule();
        if (currentModule && currentModule.loadPage) {
            currentModule.loadPage(pageNumber);
        }
    }

    getCurrentModule() {
        switch (this.currentPage) {
            case 'scraping':
                return scrapingModule;
            case 'validation':
                return validationModule;
            case 'cards':
                return cardsModule;
            case 'jobs':
                return jobsModule;
            case 'users':
                return usersModule;
            default:
                return null;
        }
    }

    logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        this.currentUser = null;
        this.navigateTo('login');
        this.showAlert('Logged out successfully', 'info');
    }

    openModal(modalId) {
        const modal = new bootstrap.Modal(document.querySelector(modalId));
        modal.show();
    }

    closeModal(modalId) {
        const modal = bootstrap.Modal.getInstance(document.querySelector(modalId));
        if (modal) {
            modal.hide();
        }
    }

    showAlert(message, type = 'info') {
        const alertContainer = document.getElementById('alertContainer');
        if (!alertContainer) return;

        const alertId = 'alert-' + Date.now();
        const alertHtml = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        alertContainer.insertAdjacentHTML('beforeend', alertHtml);

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    }

    showLoading(message = 'Loading...') {
        const loadingHtml = `
            <div id="loadingOverlay" class="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center" 
                 style="background: rgba(0,0,0,0.5); z-index: 9999;">
                <div class="bg-white p-4 rounded shadow">
                    <div class="spinner-border text-primary me-2" role="status"></div>
                    <span>${message}</span>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', loadingHtml);
    }

    hideLoading() {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.remove();
        }
    }

    formatDate(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }

    formatNumber(number) {
        if (number === null || number === undefined) return '0';
        return number.toLocaleString();
    }

    truncateText(text, maxLength = 50) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});