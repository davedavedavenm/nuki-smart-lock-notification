/**
 * Main JavaScript file for Nuki Dashboard
 */

// Document ready function
$(document).ready(function() {
    // Initialize tooltips
    initializeTooltips();
    
    // Set current year in footer
    setFooterYear();
    
    // Handle mobile navigation collapse
    setupMobileNav();
});

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Set current year in footer
function setFooterYear() {
    const currentYear = new Date().getFullYear();
    $('.footer .text-muted').text(`Nuki Smart Lock Dashboard © ${currentYear}`);
}

// Set up mobile navigation
function setupMobileNav() {
    // Close the navbar when a nav-link is clicked on mobile
    $('.navbar-nav .nav-link').on('click', function() {
        if (window.innerWidth < 992) {
            $('.navbar-collapse').collapse('hide');
        }
    });
}

// Format date and time
function formatDateTime(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleString();
}

// Format date only
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString();
}

// Format time only
function formatTime(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleTimeString();
}

// Get relative time (e.g., 5 minutes ago)
function getRelativeTime(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.round(diffMs / 1000);
    const diffMin = Math.round(diffSec / 60);
    const diffHour = Math.round(diffMin / 60);
    const diffDay = Math.round(diffHour / 24);
    
    if (diffSec < 60) {
        return `${diffSec} seconds ago`;
    } else if (diffMin < 60) {
        return `${diffMin} minutes ago`;
    } else if (diffHour < 24) {
        return `${diffHour} hours ago`;
    } else if (diffDay < 7) {
        return `${diffDay} days ago`;
    } else {
        return formatDate(date);
    }
}

// Show loading spinner
function showSpinner(elementId) {
    const html = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
    
    $(`#${elementId}`).html(html);
}

// Show error message
function showError(elementId, message) {
    const html = `
        <div class="alert alert-danger" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
        </div>
    `;
    
    $(`#${elementId}`).html(html);
}

// Copy text to clipboard
function copyToClipboard(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
}

// Format CSV data
function formatCsvData(data, headers) {
    // Create headers row
    let csv = headers.join(',') + '\n';
    
    // Add data rows
    data.forEach(row => {
        const values = headers.map(header => {
            const value = row[header] || '';
            return `"${value.toString().replace(/"/g, '""')}"`;
        });
        csv += values.join(',') + '\n';
    });
    
    return csv;
}

// Download data as CSV file
function downloadCsv(data, filename) {
    const blob = new Blob([data], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Format bytes to human-readable size
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}
