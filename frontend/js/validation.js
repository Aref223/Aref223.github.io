// Validation Module
const validationModule = {
    currentPage: 1,
    currentFilters: {},
    searchTerm: '',

    async loadValidationHistory(page = 1, filters = {}) {
        try {
            app.showLoading('Loading validation history...');
            
            this.currentPage = page;
            this.currentFilters = { ...filters };
            
            const params = {
                page: page,
                limit: 10,
                ...filters
            };

            const response = await validationAPI.getValidationHistory(params);
            this.displayValidationHistory(response.items || [], response.total || 0, response.page || 1, response.pages || 1);
            
            app.hideLoading();
        } catch (error) {
            app.hideLoading();
            app.showAlert('Failed to load validation history', 'danger');
            console.error('Validation history load error:', error);
        }
    },

    displayValidationHistory(validations, total, currentPage, totalPages) {
        const container = document.getElementById('validationHistoryList');
        if (!container) return;

        if (validations.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-shield-check"></i>
                    <h4>No validation history found</h4>
                    <p>Perform your first card validation to see results here.</p>
                    <button class="btn btn-primary" onclick="validationModule.showValidationForm()">
                        <i class="bi bi-shield-check me-2"></i>Validate Card
                    </button>
                </div>
            `;
            return;
        }

        const validationsHtml = validations.map(validation => this.createValidationCard(validation)).join('');
        container.innerHTML = validationsHtml;

        // Update pagination
        this.updatePagination(currentPage, totalPages, total);
    },

    createValidationCard(validation) {
        const statusClass = validation.is_valid ? 'bg-success' : 'bg-danger';
        const statusIcon = validation.is_valid ? 'bi-check-circle' : 'bi-x-circle';
        
        return `
            <div class="card mb-3 validation-card" data-validation-id="${validation.id}">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <div class="d-flex align-items-center mb-2">
                                <h6 class="card-title mb-0 me-3">
                                    ${validation.card_number ? `****${validation.card_number.slice(-4)}` : 'Unknown Card'}
                                </h6>
                                <span class="badge ${statusClass}">
                                    <i class="bi ${statusIcon} me-1"></i>
                                    ${validation.is_valid ? 'Valid' : 'Invalid'}
                                </span>
                            </div>
                            <p class="card-text text-muted mb-1">
                                <i class="bi bi-bank me-1"></i>
                                ${validation.bank_name || 'Unknown Bank'}
                            </p>
                            <p class="card-text text-muted mb-1">
                                <i class="bi bi-credit-card me-1"></i>
                                ${validation.card_type || 'Unknown Type'}
                            </p>
                            <p class="card-text text-muted mb-1">
                                <i class="bi bi-clock me-1"></i>
                                ${app.formatDate(validation.created_at)}
                            </p>
                            ${validation.validation_details ? `
                                <p class="card-text text-muted mb-1">
                                    <i class="bi bi-info-circle me-1"></i>
                                    ${app.truncateText(validation.validation_details, 100)}
                                </p>
                            ` : ''}
                        </div>
                        <div class="col-md-4 text-end">
                            <div class="btn-group-vertical w-100">
                                <button class="btn btn-outline-primary btn-sm mb-1" onclick="validationModule.viewValidationDetails('${validation.id}')">
                                    <i class="bi bi-eye me-1"></i>View Details
                                </button>
                                <button class="btn btn-outline-danger btn-sm mb-1" onclick="validationModule.deleteValidation('${validation.id}')">
                                    <i class="bi bi-trash me-1"></i>Delete
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    showValidationForm() {
        const modal = document.getElementById('validationModal');
        if (!modal) return;

        const modalBody = modal.querySelector('.modal-body');
        modalBody.innerHTML = `
            <form id="validationForm">
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label for="cardNumber" class="form-label">Card Number *</label>
                            <input type="text" class="form-control" id="cardNumber" name="card_number" 
                                   placeholder="1234 5678 9012 3456" required>
                        </div>
                        <div class="mb-3">
                            <label for="expiryDate" class="form-label">Expiry Date *</label>
                            <input type="text" class="form-control" id="expiryDate" name="expiry_date" 
                                   placeholder="MM/YY" required>
                        </div>
                        <div class="mb-3">
                            <label for="cvv" class="form-label">CVV *</label>
                            <input type="text" class="form-control" id="cvv" name="cvv" 
                                   placeholder="123" required>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label for="cardholderName" class="form-label">Cardholder Name</label>
                            <input type="text" class="form-control" id="cardholderName" name="cardholder_name" 
                                   placeholder="John Doe">
                        </div>
                        <div class="mb-3">
                            <label for="bankName" class="form-label">Bank Name</label>
                            <input type="text" class="form-control" id="bankName" name="bank_name" 
                                   placeholder="Bank Name">
                        </div>
                        <div class="mb-3">
                            <label for="cardType" class="form-label">Card Type</label>
                            <select class="form-select" id="cardType" name="card_type">
                                <option value="">Select Type</option>
                                <option value="visa">Visa</option>
                                <option value="mastercard">Mastercard</option>
                                <option value="amex">American Express</option>
                                <option value="discover">Discover</option>
                                <option value="other">Other</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="country" class="form-label">Country</label>
                            <input type="text" class="form-control" id="country" name="country" 
                                   placeholder="Country">
                        </div>
                    </div>
                </div>
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="includeBankInfo" name="include_bank_info" checked>
                    <label class="form-check-label" for="includeBankInfo">
                        Include bank and country information in validation
                    </label>
                </div>
            </form>
        `;

        const modalFooter = modal.querySelector('.modal-footer');
        modalFooter.innerHTML = `
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" onclick="validationModule.performValidation()">
                <i class="bi bi-shield-check me-1"></i>Validate Card
            </button>
        `;

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    },

    async performValidation() {
        const form = document.getElementById('validationForm');
        if (!form) return;

        const formData = new FormData(form);
        const validationData = {
            card_number: formData.get('card_number'),
            expiry_date: formData.get('expiry_date'),
            cvv: formData.get('cvv'),
            cardholder_name: formData.get('cardholder_name'),
            bank_name: formData.get('bank_name'),
            card_type: formData.get('card_type'),
            country: formData.get('country'),
            include_bank_info: formData.get('include_bank_info') === 'on'
        };

        try {
            app.showLoading('Validating card...');
            const result = await validationAPI.validateCard(validationData);
            app.hideLoading();
            
            app.closeModal('validationModal');
            this.showValidationResult(result);
            
            // Refresh the validation history
            this.loadValidationHistory(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Validation failed', 'danger');
        }
    },

    showValidationResult(result) {
        const modal = document.getElementById('validationResultModal');
        if (!modal) return;

        const modalBody = modal.querySelector('.modal-body');
        modalBody.innerHTML = `
            <div class="text-center mb-4">
                <i class="bi ${result.is_valid ? 'bi-check-circle text-success' : 'bi-x-circle text-danger'} fs-1"></i>
                <h4 class="mt-3">${result.is_valid ? 'Card is Valid' : 'Card is Invalid'}</h4>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <h6>Card Information</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Card Number:</strong></td><td>****${result.card_number?.slice(-4) || 'N/A'}</td></tr>
                        <tr><td><strong>Card Type:</strong></td><td>${result.card_type || 'N/A'}</td></tr>
                        <tr><td><strong>Bank:</strong></td><td>${result.bank_name || 'N/A'}</td></tr>
                        <tr><td><strong>Country:</strong></td><td>${result.country || 'N/A'}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>Validation Details</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Status:</strong></td><td><span class="badge bg-${result.is_valid ? 'success' : 'danger'}">${result.is_valid ? 'Valid' : 'Invalid'}</span></td></tr>
                        <tr><td><strong>Score:</strong></td><td>${result.validation_score || 'N/A'}</td></tr>
                        <tr><td><strong>Method:</strong></td><td>${result.validation_method || 'N/A'}</td></tr>
                        <tr><td><strong>Timestamp:</strong></td><td>${app.formatDate(result.created_at)}</td></tr>
                    </table>
                </div>
            </div>
            
            ${result.validation_details ? `
                <div class="mt-3">
                    <h6>Additional Details</h6>
                    <div class="alert alert-info">
                        ${result.validation_details}
                    </div>
                </div>
            ` : ''}
        `;

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    },

    async viewValidationDetails(validationId) {
        try {
            app.showLoading('Loading validation details...');
            const validation = await validationAPI.getValidationResult(validationId);
            app.hideLoading();
            this.showValidationDetailsModal(validation);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to load validation details', 'danger');
        }
    },

    showValidationDetailsModal(validation) {
        const modal = document.getElementById('validationDetailsModal');
        if (!modal) return;

        const modalBody = modal.querySelector('.modal-body');
        modalBody.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Card Information</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Card Number:</strong></td><td>****${validation.card_number?.slice(-4) || 'N/A'}</td></tr>
                        <tr><td><strong>Expiry Date:</strong></td><td>${validation.expiry_date || 'N/A'}</td></tr>
                        <tr><td><strong>Card Type:</strong></td><td>${validation.card_type || 'N/A'}</td></tr>
                        <tr><td><strong>Bank:</strong></td><td>${validation.bank_name || 'N/A'}</td></tr>
                        <tr><td><strong>Country:</strong></td><td>${validation.country || 'N/A'}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>Validation Results</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Status:</strong></td><td><span class="badge bg-${validation.is_valid ? 'success' : 'danger'}">${validation.is_valid ? 'Valid' : 'Invalid'}</span></td></tr>
                        <tr><td><strong>Score:</strong></td><td>${validation.validation_score || 'N/A'}</td></tr>
                        <tr><td><strong>Method:</strong></td><td>${validation.validation_method || 'N/A'}</td></tr>
                        <tr><td><strong>Validated At:</strong></td><td>${app.formatDate(validation.created_at)}</td></tr>
                        <tr><td><strong>Validated By:</strong></td><td>${validation.user?.username || 'N/A'}</td></tr>
                    </table>
                </div>
            </div>
            
            ${validation.validation_details ? `
                <div class="mt-3">
                    <h6>Validation Details</h6>
                    <div class="alert alert-info">
                        ${validation.validation_details}
                    </div>
                </div>
            ` : ''}
        `;

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    },

    async deleteValidation(validationId) {
        if (!confirm('Are you sure you want to delete this validation record? This action cannot be undone.')) return;

        try {
            app.showLoading('Deleting validation record...');
            await validationAPI.deleteValidationResult(validationId);
            app.hideLoading();
            app.showAlert('Validation record deleted successfully', 'success');
            this.loadValidationHistory(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to delete validation record', 'danger');
        }
    },

    updatePagination(currentPage, totalPages, total) {
        const paginationContainer = document.getElementById('validationPagination');
        if (!paginationContainer) return;

        if (totalPages <= 1) {
            paginationContainer.innerHTML = '';
            return;
        }

        let paginationHtml = `
            <nav aria-label="Validation history pagination">
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
                Showing ${((currentPage - 1) * 10) + 1} to ${Math.min(currentPage * 10, total)} of ${total} validations
            </div>
        `;

        paginationContainer.innerHTML = paginationHtml;
    },

    searchHistory(searchTerm) {
        this.searchTerm = searchTerm;
        this.currentPage = 1;
        this.loadValidationHistory(1, { search: searchTerm });
    },

    applyFilters(filters) {
        this.currentFilters = { ...filters };
        this.currentPage = 1;
        this.loadValidationHistory(1, this.currentFilters);
    },

    loadPage(pageNumber) {
        this.loadValidationHistory(pageNumber, this.currentFilters);
    },

    refreshHistory() {
        this.loadValidationHistory(this.currentPage, this.currentFilters);
    }
};

// Export for global use
window.validationModule = validationModule;