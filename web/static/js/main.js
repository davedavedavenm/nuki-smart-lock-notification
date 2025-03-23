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
    
    // Initialize theme toggler if present
    setupThemeToggle();
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

// Setup theme toggle
function setupThemeToggle() {
    $('#themeToggle').on('click', function() {
        // Get current theme
        const currentTheme = $('body').hasClass('dark-theme') ? 'dark' : 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        console.log("Theme toggle clicked, changing from", currentTheme, "to", newTheme);
        
        // Update theme via AJAX
        $.ajax({
            url: '/api/theme',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                theme: newTheme
            }),
            success: function(response) {
                console.log("Theme updated successfully:", response);
                // Reload page to apply new theme
                location.reload();
            },
            error: function(xhr, status, error) {
                console.error('Error updating theme:', error);
                alert('Failed to update theme preference: ' + error);
            }
        });
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
function showError(elementId, message, retryFunc = null) {
    const retryButton = retryFunc ? 
        `<button type="button" class="btn btn-link btn-sm retry-btn">Retry</button>` : '';
    
    const html = `
        <div class="alert alert-danger" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
            ${retryButton}
        </div>
    `;
    
    $(`#${elementId}`).html(html);
    
    // Add retry functionality if a function was provided
    if (retryFunc) {
        $(`#${elementId} .retry-btn`).on('click', function() {
            showSpinner(elementId);
            setTimeout(retryFunc, 500); // Slight delay to show spinner
        });
    }
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

// Generic API request function with error handling
function makeApiRequest(url, method = 'GET', data = null, successCallback, errorCallback) {
    const options = {
        url: url,
        type: method,
        dataType: 'json',
        timeout: 15000, // 15 second timeout
        success: function(response) {
            if (successCallback && typeof successCallback === 'function') {
                successCallback(response);
            }
        },
        error: function(xhr, status, error) {
            console.error(`API Error (${url}):`, error);
            let errorMessage = 'An error occurred while communicating with the server.';
            
            if (xhr.responseJSON && xhr.responseJSON.error) {
                errorMessage = xhr.responseJSON.error;
            } else if (status === 'timeout') {
                errorMessage = 'The request timed out. Please check your connection and try again.';
            } else if (xhr.status === 0) {
                errorMessage = 'Could not connect to the server. Please check your connection.';
            } else if (xhr.status === 401 || xhr.status === 403) {
                errorMessage = 'Authentication error. Please log in again.';
                // Redirect to login after 2 seconds
                setTimeout(function() {
                    window.location.href = '/login';
                }, 2000);
            } else if (xhr.status === 404) {
                errorMessage = 'The requested resource was not found.';
            } else if (xhr.status >= 500) {
                errorMessage = 'A server error occurred. Please try again later.';
            }
            
            if (errorCallback && typeof errorCallback === 'function') {
                errorCallback(errorMessage, xhr);
            } else {
                console.error(errorMessage);
            }
        }
    };
    
    // Add data if provided
    if (data) {
        if (method === 'GET') {
            options.data = data;
        } else {
            options.contentType = 'application/json';
            options.data = JSON.stringify(data);
        }
    }
    
    // Make the request
    $.ajax(options);
}

// Health check for the dashboard
function checkHealth() {
    $.ajax({
        url: '/health',
        method: 'GET',
        dataType: 'json',
        timeout: 5000,
        success: function(data) {
            console.log('Health check successful:', data);
            // If there are any error indicators on the page, try to refresh them
            if ($('.alert-danger').length > 0) {
                console.log('Found error indicators, attempting refresh');
                if (typeof loadDashboardData === 'function') {
                    loadDashboardData();
                }
                if (typeof loadRecentActivity === 'function') {
                    loadRecentActivity();
                }
                if (typeof loadUserActivityChart === 'function') {
                    loadUserActivityChart();
                }
            }
        },
        error: function(xhr, status, error) {
            console.error('Health check failed:', error);
        }
    });
}

// Run a health check periodically 
$(document).ready(function() {
    // Initial health check after 5 seconds
    setTimeout(checkHealth, 5000);
    
    // Then every 30 seconds
    setInterval(checkHealth, 30000);
});
