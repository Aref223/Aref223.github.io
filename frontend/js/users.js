// Users Module
const usersModule = {
    currentPage: 1,
    currentFilters: {},
    searchTerm: '',

    async loadUsers(page = 1, filters = {}) {
        try {
            app.showLoading('Loading users...');
            
            this.currentPage = page;
            this.currentFilters = { ...filters };
            
            const params = {
                page: page,
                limit: 10,
                ...filters
            };

            const response = await usersAPI.getUsers(params);
            this.displayUsers(response.items || [], response.total || 0, response.page || 1, response.pages || 1);
            
            app.hideLoading();
        } catch (error) {
            app.hideLoading();
            app.showAlert('Failed to load users', 'danger');
            console.error('Users load error:', error);
        }
    },

    displayUsers(users, total, currentPage, totalPages) {
        const container = document.getElementById('usersList');
        if (!container) return;

        if (users.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-people"></i>
                    <h4>No users found</h4>
                    <p>No users have been created yet.</p>
                    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addUserModal">
                        <i class="bi bi-plus-circle me-2"></i>Add User
                    </button>
                </div>
            `;
            return;
        }

        const usersHtml = users.map(user => this.createUserItem(user)).join('');
        container.innerHTML = usersHtml;

        // Update pagination
        this.updatePagination(currentPage, totalPages, total);
    },

    createUserItem(user) {
        const statusClass = user.is_active ? 'bg-success' : 'bg-danger';
        const statusText = user.is_active ? 'Active' : 'Inactive';
        const roleClass = this.getRoleClass(user.role);
        
        return `
            <div class="card mb-3 user-item" data-user-id="${user.id}">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <div class="d-flex align-items-center mb-2">
                                <h6 class="card-title mb-0 me-3">
                                    ${user.first_name} ${user.last_name}
                                </h6>
                                <span class="badge ${statusClass} me-2">${statusText}</span>
                                <span class="badge ${roleClass}">${user.role}</span>
                            </div>
                            <p class="card-text text-muted mb-1">
                                <i class="bi bi-person me-1"></i>
                                ${user.username}
                            </p>
                            <p class="card-text text-muted mb-1">
                                <i class="bi bi-envelope me-1"></i>
                                ${user.email}
                            </p>
                            ${user.phone ? `
                                <p class="card-text text-muted mb-1">
                                    <i class="bi bi-telephone me-1"></i>
                                    ${user.phone}
                                </p>
                            ` : ''}
                            <p class="card-text text-muted mb-1">
                                <i class="bi bi-clock me-1"></i>
                                Joined: ${app.formatDate(user.created_at)}
                            </p>
                            ${user.last_login ? `
                                <p class="card-text text-muted mb-1">
                                    <i class="bi bi-box-arrow-in-right me-1"></i>
                                    Last login: ${app.formatDate(user.last_login)}
                                </p>
                            ` : ''}
                        </div>
                        <div class="col-md-4 text-end">
                            <div class="btn-group-vertical w-100">
                                <button class="btn btn-outline-primary btn-sm mb-1" onclick="usersModule.viewUserDetails('${user.id}')">
                                    <i class="bi bi-eye me-1"></i>View
                                </button>
                                <button class="btn btn-outline-warning btn-sm mb-1" onclick="usersModule.editUser('${user.id}')">
                                    <i class="bi bi-pencil me-1"></i>Edit
                                </button>
                                ${user.is_active ? `
                                    <button class="btn btn-outline-danger btn-sm mb-1" onclick="usersModule.deactivateUser('${user.id}')">
                                        <i class="bi bi-person-x me-1"></i>Deactivate
                                    </button>
                                ` : `
                                    <button class="btn btn-outline-success btn-sm mb-1" onclick="usersModule.activateUser('${user.id}')">
                                        <i class="bi bi-person-check me-1"></i>Activate
                                    </button>
                                `}
                                ${user.id !== app.currentUser?.id ? `
                                    <button class="btn btn-outline-danger btn-sm mb-1" onclick="usersModule.deleteUser('${user.id}')">
                                        <i class="bi bi-trash me-1"></i>Delete
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    getRoleClass(role) {
        const roleClasses = {
            'admin': 'bg-danger',
            'scraper': 'bg-warning',
            'user': 'bg-info'
        };
        return roleClasses[role] || 'bg-secondary';
    },

    async viewUserDetails(userId) {
        try {
            app.showLoading('Loading user details...');
            const user = await usersAPI.getUser(userId);
            app.hideLoading();
            this.showUserDetailsModal(user);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to load user details', 'danger');
        }
    },

    showUserDetailsModal(user) {
        const modal = document.getElementById('userDetailsModal');
        if (!modal) return;

        const modalBody = modal.querySelector('.modal-body');
        modalBody.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Personal Information</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Username:</strong></td><td>${user.username}</td></tr>
                        <tr><td><strong>First Name:</strong></td><td>${user.first_name || 'N/A'}</td></tr>
                        <tr><td><strong>Last Name:</strong></td><td>${user.last_name || 'N/A'}</td></tr>
                        <tr><td><strong>Email:</strong></td><td>${user.email}</td></tr>
                        <tr><td><strong>Phone:</strong></td><td>${user.phone || 'N/A'}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>Account Information</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Role:</strong></td><td><span class="badge ${this.getRoleClass(user.role)}">${user.role}</span></td></tr>
                        <tr><td><strong>Status:</strong></td><td><span class="badge bg-${user.is_active ? 'success' : 'danger'}">${user.is_active ? 'Active' : 'Inactive'}</span></td></tr>
                        <tr><td><strong>Email Verified:</strong></td><td><span class="badge bg-${user.email_verified ? 'success' : 'warning'}">${user.email_verified ? 'Yes' : 'No'}</span></td></tr>
                        <tr><td><strong>Joined:</strong></td><td>${app.formatDate(user.created_at)}</td></tr>
                        <tr><td><strong>Last Login:</strong></td><td>${user.last_login ? app.formatDate(user.last_login) : 'Never'}</td></tr>
                    </table>
                </div>
            </div>
            
            ${user.activity_stats ? `
                <div class="mt-3">
                    <h6>Activity Statistics</h6>
                    <div class="row">
                        <div class="col-md-3">
                            <div class="text-center">
                                <h5 class="text-primary">${user.activity_stats.total_jobs || 0}</h5>
                                <small class="text-muted">Total Jobs</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <h5 class="text-success">${user.activity_stats.completed_jobs || 0}</h5>
                                <small class="text-muted">Completed Jobs</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <h5 class="text-info">${user.activity_stats.total_validations || 0}</h5>
                                <small class="text-muted">Validations</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <h5 class="text-warning">${user.activity_stats.total_cards || 0}</h5>
                                <small class="text-muted">Cards Added</small>
                            </div>
                        </div>
                    </div>
                </div>
            ` : ''}
        `;

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    },

    async editUser(userId) {
        try {
            app.showLoading('Loading user data...');
            const user = await usersAPI.getUser(userId);
            app.hideLoading();
            this.showEditUserModal(user);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to load user data', 'danger');
        }
    },

    showEditUserModal(user) {
        const modal = document.getElementById('editUserModal');
        if (!modal) return;

        const modalBody = modal.querySelector('.modal-body');
        modalBody.innerHTML = `
            <form id="editUserForm">
                <input type="hidden" name="user_id" value="${user.id}">
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label for="editUsername" class="form-label">Username *</label>
                            <input type="text" class="form-control" id="editUsername" name="username" 
                                   value="${user.username}" required>
                        </div>
                        <div class="mb-3">
                            <label for="editEmail" class="form-label">Email *</label>
                            <input type="email" class="form-control" id="editEmail" name="email" 
                                   value="${user.email}" required>
                        </div>
                        <div class="mb-3">
                            <label for="editFirstName" class="form-label">First Name</label>
                            <input type="text" class="form-control" id="editFirstName" name="first_name" 
                                   value="${user.first_name || ''}">
                        </div>
                        <div class="mb-3">
                            <label for="editLastName" class="form-label">Last Name</label>
                            <input type="text" class="form-control" id="editLastName" name="last_name" 
                                   value="${user.last_name || ''}">
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label for="editPhone" class="form-label">Phone</label>
                            <input type="tel" class="form-control" id="editPhone" name="phone" 
                                   value="${user.phone || ''}">
                        </div>
                        <div class="mb-3">
                            <label for="editRole" class="form-label">Role *</label>
                            <select class="form-select" id="editRole" name="role" required>
                                <option value="user" ${user.role === 'user' ? 'selected' : ''}>User</option>
                                <option value="scraper" ${user.role === 'scraper' ? 'selected' : ''}>Scraper</option>
                                <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>Admin</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="editPassword" class="form-label">New Password</label>
                            <input type="password" class="form-control" id="editPassword" name="password" 
                                   placeholder="Leave blank to keep current password">
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="editIsActive" name="is_active" 
                                   ${user.is_active ? 'checked' : ''}>
                            <label class="form-check-label" for="editIsActive">
                                Active Account
                            </label>
                        </div>
                    </div>
                </div>
            </form>
        `;

        const modalFooter = modal.querySelector('.modal-footer');
        modalFooter.innerHTML = `
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" onclick="usersModule.updateUser()">
                <i class="bi bi-check-circle me-1"></i>Update User
            </button>
        `;

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    },

    async updateUser() {
        const form = document.getElementById('editUserForm');
        if (!form) return;

        const formData = new FormData(form);
        const userId = formData.get('user_id');
        const userData = {
            username: formData.get('username'),
            email: formData.get('email'),
            first_name: formData.get('first_name'),
            last_name: formData.get('last_name'),
            phone: formData.get('phone'),
            role: formData.get('role'),
            is_active: formData.get('is_active') === 'on'
        };

        // Only include password if provided
        const password = formData.get('password');
        if (password) {
            userData.password = password;
        }

        try {
            app.showLoading('Updating user...');
            await usersAPI.updateUser(userId, userData);
            app.hideLoading();
            app.showAlert('User updated successfully', 'success');
            app.closeModal('editUserModal');
            this.loadUsers(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to update user', 'danger');
        }
    },

    async activateUser(userId) {
        try {
            app.showLoading('Activating user...');
            await usersAPI.activateUser(userId);
            app.hideLoading();
            app.showAlert('User activated successfully', 'success');
            this.loadUsers(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to activate user', 'danger');
        }
    },

    async deactivateUser(userId) {
        if (!confirm('Are you sure you want to deactivate this user?')) return;

        try {
            app.showLoading('Deactivating user...');
            await usersAPI.deactivateUser(userId);
            app.hideLoading();
            app.showAlert('User deactivated successfully', 'success');
            this.loadUsers(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to deactivate user', 'danger');
        }
    },

    async deleteUser(userId) {
        if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) return;

        try {
            app.showLoading('Deleting user...');
            await usersAPI.deleteUser(userId);
            app.hideLoading();
            app.showAlert('User deleted successfully', 'success');
            this.loadUsers(this.currentPage, this.currentFilters);
        } catch (error) {
            app.hideLoading();
            app.showAlert(error.message || 'Failed to delete user', 'danger');
        }
    },

    updatePagination(currentPage, totalPages, total) {
        const paginationContainer = document.getElementById('usersPagination');
        if (!paginationContainer) return;

        if (totalPages <= 1) {
            paginationContainer.innerHTML = '';
            return;
        }

        let paginationHtml = `
            <nav aria-label="Users pagination">
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
                Showing ${((currentPage - 1) * 10) + 1} to ${Math.min(currentPage * 10, total)} of ${total} users
            </div>
        `;

        paginationContainer.innerHTML = paginationHtml;
    },

    searchUsers(searchTerm) {
        this.searchTerm = searchTerm;
        this.currentPage = 1;
        this.loadUsers(1, { search: searchTerm });
    },

    applyFilters(filters) {
        this.currentFilters = { ...filters };
        this.currentPage = 1;
        this.loadUsers(1, this.currentFilters);
    },

    loadPage(pageNumber) {
        this.loadUsers(pageNumber, this.currentFilters);
    },

    refreshUsers() {
        this.loadUsers(this.currentPage, this.currentFilters);
    }
};

// Export for global use
window.usersModule = usersModule;