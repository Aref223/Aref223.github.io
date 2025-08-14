// Cards Module
const cardsModule = {
    currentPage: 1,
    currentFilters: {},
    searchTerm: '',

    async loadCards(page = 1, filters = {}) {
        try {
            app.showLoading('Loading cards...');
            
            this.currentPage = page;
            this.currentFilters = { ...filters };
            
            const params = {
                page: page,
                limit: 10,
                ...filters
            };

            const response = await cardsAPI.getCards(params);
            this.displayCards(response.items || [], response.total || 0, response.page || 1, response.pages || 1);
            
            app.hideLoading();
        } catch (error) {
            app.hideLoading();
            app.showAlert('Failed to load cards', 'danger');
            console.error('Cards load error:', error);
        }
    },

    displayCards(cards, total, currentPage, totalPages) {
        const container = document.getElementById('cardsList');
        if (!container) return;

        if (cards.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-credit-card"></i>
                    <h4>No cards found</h4>
                    <p>Add your first card to get started.</p>
                    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addCardModal">
                        <i class="bi bi-plus-circle me-2"></i>Add Card
                    </button>
                </div>
            `;
            return;
        }

        const cardsHtml = cards.map(card => this.createCardItem(card)).join('');
        container.innerHTML = cardsHtml;

        // Update pagination
        this.updatePagination(currentPage, totalPages, total);
    },

    createCardItem(card) {
        const statusClass = card.is_valid ? 'bg-success' : 'bg-warning';
        const statusText = card.is_valid ? 'Valid' : 'Pending';
        
        return `
            <div class="card mb-3 card-item" data-card-id="${card.id}">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <div class="d-flex align-items-center mb-2">
                                <h6 class="card-title mb-0 me-3">
                                    ${card.cardholder_name || 'Unknown Cardholder'}
                                </h6>
                                <span class="badge ${statusClass}">${statusText}</span>
                            </div>
                            <p class="card-text text-muted mb-1">
                                <i class="bi bi-credit-card me-1"></i>
                                ****${card.card_number?.slice(-4) || '****'}
                            </p>
                            <p class="card-text text-muted mb-1">
                                <i class="bi bi-bank me-1"></i>
                                ${card.bank_name || 'Unknown Bank'}
                            </p>
                            <p class="card-text text-muted mb-1">
                                <i class="bi bi-tag me-1"></i>
                                ${card.card_type || 'Unknown Type'}
                            </p>
                            <p class="card-text text-muted mb-1">
                                <i class="bi bi-clock me-1"></i>
                                Added: ${app.formatDate(card.created_at)}
                            </p>
                            ${card.last_validated_at ? `
                                <p class="card-text text-muted mb-1">
                                    <i class="bi bi-shield-check me-1"></i>
                                    Last validated: ${app.formatDate(card.last_validated_at)}
                                </p>
                            ` : ''}
                        </div>
                        <div class="col-md-4 text-end">
                            <div class="btn-group-vertical w-100">
                                <button class="btn btn-outline-primary btn-sm mb-1" onclick="cardsModule.viewCardDetails('${card.id}')">
                                    <i class="bi bi-eye me-1"></i>View
                                </button>
                                <button class="btn btn-outline-success btn-sm mb-1" onclick="cardsModule.validateCard('${card.id}')">
                                    <i class="bi bi-shield-check me-1"></i>Validate
                                </button>
                                <button class="btn btn-outline-warning btn-sm mb-1" onclick="cardsModule.editCard('${card.id}')">
                                    <i class="bi bi-pencil me-1"></i>Edit
                                </button>
                                <button class="btn btn-outline-danger btn-sm mb-1" onclick="cardsModule.deleteCard('${card.id}')">
                                    <i class="bi bi-trash me-1"></i>Delete
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    async viewCardDetails(cardId) {
        try {
            app.showLoading('Loading card details...');
            const card = await cardsAPI.getCard(cardId);
            app.hideLoading();
            this.showCardDetailsModal(card);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to load card details', 'danger');
        }
    },

    showCardDetailsModal(card) {
        const modal = document.getElementById('cardDetailsModal');
        if (!modal) return;

        const modalBody = modal.querySelector('.modal-body');
        modalBody.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Card Information</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Card Number:</strong></td><td>****${card.card_number?.slice(-4) || '****'}</td></tr>
                        <tr><td><strong>Expiry Date:</strong></td><td>${card.expiry_date || 'N/A'}</td></tr>
                        <tr><td><strong>Cardholder:</strong></td><td>${card.cardholder_name || 'N/A'}</td></tr>
                        <tr><td><strong>Bank:</strong></td><td>${card.bank_name || 'N/A'}</td></tr>
                        <tr><td><strong>Card Type:</strong></td><td>${card.card_type || 'N/A'}</td></tr>
                        <tr><td><strong>Country:</strong></td><td>${card.country || 'N/A'}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>Validation Status</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Status:</strong></td><td><span class="badge bg-${card.is_valid ? 'success' : 'warning'}">${card.is_valid ? 'Valid' : 'Pending'}</span></td></tr>
                        <tr><td><strong>Added:</strong></td><td>${app.formatDate(card.created_at)}</td></tr>
                        <tr><td><strong>Last Validated:</strong></td><td>${card.last_validated_at ? app.formatDate(card.last_validated_at) : 'Never'}</td></tr>
                        <tr><td><strong>Added By:</strong></td><td>${card.user?.username || 'N/A'}</td></tr>
                    </table>
                </div>
            </div>
            
            ${card.validation_history && card.validation_history.length > 0 ? `
                <div class="mt-3">
                    <h6>Validation History</h6>
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Status</th>
                                    <th>Score</th>
                                    <th>Method</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${card.validation_history.map(validation => `
                                    <tr>
                                        <td>${app.formatDate(validation.created_at)}</td>
                                        <td><span class="badge bg-${validation.is_valid ? 'success' : 'danger'}">${validation.is_valid ? 'Valid' : 'Invalid'}</span></td>
                                        <td>${validation.validation_score || 'N/A'}</td>
                                        <td>${validation.validation_method || 'N/A'}</td>
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

    async validateCard(cardId) {
        try {
            app.showLoading('Validating card...');
            const result = await cardsAPI.validateCard(cardId);
            app.hideLoading();
            
            this.showValidationResult(result);
            
            // Refresh the cards list
            this.loadCards(this.currentPage, this.currentFilters);
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

    async editCard(cardId) {
        try {
            app.showLoading('Loading card data...');
            const card = await cardsAPI.getCard(cardId);
            app.hideLoading();
            this.showEditCardModal(card);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to load card data', 'danger');
        }
    },

    showEditCardModal(card) {
        const modal = document.getElementById('editCardModal');
        if (!modal) return;

        const modalBody = modal.querySelector('.modal-body');
        modalBody.innerHTML = `
            <form id="editCardForm">
                <input type="hidden" name="card_id" value="${card.id}">
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label for="editCardNumber" class="form-label">Card Number *</label>
                            <input type="text" class="form-control" id="editCardNumber" name="card_number" 
                                   value="${card.card_number || ''}" required>
                        </div>
                        <div class="mb-3">
                            <label for="editExpiryDate" class="form-label">Expiry Date *</label>
                            <input type="text" class="form-control" id="editExpiryDate" name="expiry_date" 
                                   value="${card.expiry_date || ''}" required>
                        </div>
                        <div class="mb-3">
                            <label for="editCvv" class="form-label">CVV *</label>
                            <input type="text" class="form-control" id="editCvv" name="cvv" 
                                   value="${card.cvv || ''}" required>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label for="editCardholderName" class="form-label">Cardholder Name</label>
                            <input type="text" class="form-control" id="editCardholderName" name="cardholder_name" 
                                   value="${card.cardholder_name || ''}">
                        </div>
                        <div class="mb-3">
                            <label for="editBankName" class="form-label">Bank Name</label>
                            <input type="text" class="form-control" id="editBankName" name="bank_name" 
                                   value="${card.bank_name || ''}">
                        </div>
                        <div class="mb-3">
                            <label for="editCardType" class="form-label">Card Type</label>
                            <select class="form-select" id="editCardType" name="card_type">
                                <option value="">Select Type</option>
                                <option value="visa" ${card.card_type === 'visa' ? 'selected' : ''}>Visa</option>
                                <option value="mastercard" ${card.card_type === 'mastercard' ? 'selected' : ''}>Mastercard</option>
                                <option value="amex" ${card.card_type === 'amex' ? 'selected' : ''}>American Express</option>
                                <option value="discover" ${card.card_type === 'discover' ? 'selected' : ''}>Discover</option>
                                <option value="other" ${card.card_type === 'other' ? 'selected' : ''}>Other</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="editCountry" class="form-label">Country</label>
                            <input type="text" class="form-control" id="editCountry" name="country" 
                                   value="${card.country || ''}">
                        </div>
                    </div>
                </div>
            </form>
        `;

        const modalFooter = modal.querySelector('.modal-footer');
        modalFooter.innerHTML = `
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" onclick="cardsModule.updateCard()">
                <i class="bi bi-check-circle me-1"></i>Update Card
            </button>
        `;

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    },

    async updateCard() {
        const form = document.getElementById('editCardForm');
        if (!form) return;

        const formData = new FormData(form);
        const cardId = formData.get('card_id');
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
            app.showLoading('Updating card...');
            await cardsAPI.updateCard(cardId, cardData);
            app.hideLoading();
            app.showAlert('Card updated successfully', 'success');
            app.closeModal('editCardModal');
            this.loadCards(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to update card', 'danger');
        }
    },

    async deleteCard(cardId) {
        if (!confirm('Are you sure you want to delete this card? This action cannot be undone.')) return;

        try {
            app.showLoading('Deleting card...');
            await cardsAPI.deleteCard(cardId);
            app.hideLoading();
            app.showAlert('Card deleted successfully', 'success');
            this.loadCards(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to delete card', 'danger');
        }
    },

    updatePagination(currentPage, totalPages, total) {
        const paginationContainer = document.getElementById('cardsPagination');
        if (!paginationContainer) return;

        if (totalPages <= 1) {
            paginationContainer.innerHTML = '';
            return;
        }

        let paginationHtml = `
            <nav aria-label="Cards pagination">
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
                Showing ${((currentPage - 1) * 10) + 1} to ${Math.min(currentPage * 10, total)} of ${total} cards
            </div>
        `;

        paginationContainer.innerHTML = paginationHtml;
    },

    searchCards(searchTerm) {
        this.searchTerm = searchTerm;
        this.currentPage = 1;
        this.loadCards(1, { search: searchTerm });
    },

    applyFilters(filters) {
        this.currentFilters = { ...filters };
        this.currentPage = 1;
        this.loadCards(1, this.currentFilters);
    },

    loadPage(pageNumber) {
        this.loadCards(pageNumber, this.currentFilters);
    },

    refreshCards() {
        this.loadCards(this.currentPage, this.currentFilters);
    }
};

// Export for global use
window.cardsModule = cardsModule;