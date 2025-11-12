// Main JavaScript for FeminineCare Tracker

// DOM Elements
const sidebar = document.getElementById('desktop-sidebar');
const sidebarToggle = document.getElementById('sidebar-toggle');
const mobileCalendarToggle = document.getElementById('mobile-calendar-toggle');
const mobileCalendarView = document.getElementById('mobile-calendar-view');

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Sidebar toggle
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }
    
    // Mobile calendar toggle
    if (mobileCalendarToggle) {
        mobileCalendarToggle.addEventListener('click', toggleMobileCalendar);
    }
    
    // Initialize all modals
    initializeModals();
    
    // Initialize support/legal toggles
    initializeSupportLegalToggles();
    
    // Auto-hide flash messages
    autoHideFlashMessages();
});

// Toggle sidebar collapse
function toggleSidebar() {
    sidebar.classList.toggle('collapsed');
    const icon = document.getElementById('sidebar-toggle-icon');
    icon.textContent = sidebar.classList.contains('collapsed') ? 'menu_open' : 'menu_open';
}

// Toggle mobile calendar view
function toggleMobileCalendar() {
    if (mobileCalendarView) {
        mobileCalendarView.classList.toggle('hidden');
    }
}

// Initialize all modals
function initializeModals() {
    // Add Period Modal
    const addPeriodModal = document.getElementById('addPeriodModal');
    if (addPeriodModal) {
        window.toggleAddPeriodModal = function(periodId = null, startDate = '', endDate = '', notes = '') {
            const form = addPeriodModal.querySelector('form');
            
            if (periodId) {
                form.action = `/update_period/${periodId}`;
                document.getElementById('start-date').value = startDate;
                document.getElementById('end-date').value = endDate;
                document.getElementById('notes').value = notes;
            } else {
                form.action = '/add_period';
                form.reset();
            }
            
            toggleModal(addPeriodModal);
        };
        
        window.editPeriod = function(periodId, startDate, endDate, notes) {
            window.toggleAddPeriodModal(periodId, startDate, endDate, notes);
        };
    }
    
    // Add Product Modal
    const addProductModal = document.getElementById('addProductModal');
    if (addProductModal) {
        window.toggleAddProductModal = function(productId = null, name = '', category = '', quantity = '') {
            const form = addProductModal.querySelector('form');
            
            if (productId) {
                form.action = `/update_product/${productId}`;
                document.getElementById('name').value = name;
                document.getElementById('category').value = category;
                document.getElementById('quantity').value = quantity;
            } else {
                form.action = '/add_product';
                form.reset();
            }
            
            toggleModal(addProductModal);
        };
        
        window.editProduct = function(productId, name, category, quantity) {
            window.toggleAddProductModal(productId, name, category, quantity);
        };
    }
    
    // Add Medication Modal
    const addMedicationModal = document.getElementById('addMedicationModal');
    if (addMedicationModal) {
        window.toggleAddMedicationModal = function(medId = null, name = '', dosage = '', frequency = '', timeOfDay = '', quantity = '') {
            const form = addMedicationModal.querySelector('form');
            
            if (medId) {
                form.action = `/update_medication/${medId}`;
                document.getElementById('name').value = name;
                document.getElementById('dosage').value = dosage;
                document.getElementById('frequency').value = frequency;
                document.getElementById('time_of_day').value = timeOfDay;
                document.getElementById('quantity').value = quantity;
            } else {
                form.action = '/add_medication';
                form.reset();
            }
            
            toggleModal(addMedicationModal);
        };
        
        window.editMedication = function(medId, name, dosage, frequency, timeOfDay, quantity) {
            window.toggleAddMedicationModal(medId, name, dosage, frequency, timeOfDay, quantity);
        };
    }
}

// Toggle modal visibility
function toggleModal(modal) {
    modal.classList.toggle('opacity-0');
    modal.classList.toggle('pointer-events-none');
}

// Initialize support/legal toggles
function initializeSupportLegalToggles() {
    const toggles = document.querySelectorAll('.support-legal-toggle');
    
    toggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const content = this.nextElementSibling;
            const icon = this.querySelector('.support-legal-icon');
            
            content.classList.toggle('hidden');
            icon.textContent = content.classList.contains('hidden') ? 'chevron_right' : 'expand_more';
        });
    });
}

// Auto-hide flash messages
function autoHideFlashMessages() {
    const flashContainer = document.getElementById('flash-message-container');
    
    if (flashContainer) {
        setTimeout(() => {
            flashContainer.style.transition = 'opacity 0.5s ease';
            flashContainer.style.opacity = '0';
            
            setTimeout(() => {
                flashContainer.remove();
            }, 500);
        }, 3000);
    }
}

// Profile functions
function toggleProfileEdit() {
    const profileInfoDisplay = document.getElementById('profileInfoDisplay');
    const profileEditForm = document.getElementById('profileEditForm');
    
    profileInfoDisplay.classList.toggle('hidden');
    profileEditForm.classList.toggle('hidden');
}

function toggleProfileImageEdit() {
    const profileImageEditForm = document.getElementById('profileImageEditForm');
    profileImageEditForm.classList.toggle('hidden');
}

function saveProfileImage() {
    const input = document.getElementById('profileImageInput');
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('profileImageContainer').style.backgroundImage = `url(${e.target.result})`;
            toggleProfileImageEdit();
            showNotification('Profile image updated successfully!', 'success');
        };
        reader.readAsDataURL(input.files[0]);
    } else {
        toggleProfileImageEdit();
    }
}

function confirmDeleteAccount() {
    if (confirm("Are you sure you want to delete your account? This action cannot be undone.")) {
        showNotification('Account deletion would be processed here', 'info');
    }
}

// View toggle functions
function toggleView(view) {
    const upcomingView = document.getElementById('upcomingView');
    const historyView = document.getElementById('historyView');
    
    if (view === 'upcoming') {
        upcomingView.classList.remove('hidden');
        historyView.classList.add('hidden');
    } else {
        upcomingView.classList.add('hidden');
        historyView.classList.remove('hidden');
    }
}

// Utility functions
function showNotification(message, type = 'info') {
    const flashContainer = document.getElementById('flash-message-container');
    
    if (!flashContainer) {
        const container = document.createElement('div');
        container.id = 'flash-message-container';
        container.className = 'fixed top-4 right-4 z-50 md:top-6 md:right-8 space-y-2';
        document.body.appendChild(container);
    }
    
    const notification = document.createElement('div');
    notification.className = `px-4 py-3 rounded-lg ${
        type === 'success' ? 'bg-green-500 text-white' :
        type === 'danger' ? 'bg-red-500 text-white' :
        type === 'warning' ? 'bg-alert text-white' :
        'bg-blue-500 text-white'
    }`;
    notification.textContent = message;
    
    flashContainer.appendChild(notification);
    
    setTimeout(() => {
        notification.style.transition = 'opacity 0.5s ease';
        notification.style.opacity = '0';
        
        setTimeout(() => {
            notification.remove();
        }, 500);
    }, 3000);
}

// Password visibility toggle
function togglePassword(fieldId) {
    const field = document.getElementById(fieldId);
    const icon = document.getElementById(fieldId + '-icon');
    
    if (field.type === 'password') {
        field.type = 'text';
        icon.textContent = 'visibility';
    } else {
        field.type = 'password';
        icon.textContent = 'visibility_off';
    }
}