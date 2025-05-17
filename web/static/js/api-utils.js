/**
 * Enhanced API Utilities for Nuki Dashboard
 * Provides robust error handling and improved data loading
 */

// Improved API request with retry capabilities
function fetchApiData(url, elementId, processFunc, method = 'GET', data = null, retries = 3, delay = 1000) {
    // Show loading spinner
    if (elementId) {
        $(`#${elementId}`).html(`
            <div class="d-flex justify-content-center align-items-center" style="min-height: 150px;">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `);
    }
    
    // Setup request options
    const options = {
        url: url,
        type: method,
        dataType: 'json',
        timeout: 20000, // 20 second timeout
        success: function(response) {
            console.log(`API success (${url})`, response);
            if (processFunc && typeof processFunc === 'function') {
                try {
                    processFunc(response);
                } catch (err) {
                    console.error('Error processing API response:', err);
                    if (elementId) {
                        showApiError(elementId, 'Error processing data', () => {
                            fetchApiData(url, elementId, processFunc, method, data, retries, delay);
                        });
                    }
                }
            }
        },
        error: function(xhr, status, error) {
            console.error(`API Error (${url}):`, {status, error, xhr});
            
            // Determine if we should retry
            if (retries > 0) {
                console.log(`Retrying API call in ${delay}ms (${retries} retries left)`);
                setTimeout(() => {
                    fetchApiData(url, elementId, processFunc, method, data, retries - 1, delay * 1.5);
                }, delay);
                return;
            }
            
            // No more retries, display error
            if (elementId) {
                let errorMessage = getApiErrorMessage(xhr, status, error);
                showApiError(elementId, errorMessage, () => {
                    fetchApiData(url, elementId, processFunc, method, data, 3, 1000);
                });
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

// Show API error with retry option
function showApiError(elementId, message, retryFunc = null) {
    const retryButton = retryFunc ? 
        `<button type="button" class="btn btn-primary btn-sm mt-2 retry-btn">
            <i class="fas fa-sync-alt me-1"></i>Retry
        </button>` : '';
    
    const html = `
        <div class="api-error text-center p-4">
            <div class="alert alert-danger" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>Error:</strong> ${message}
            </div>
            <div class="error-details small text-muted mb-2">
                If this problem persists, please check your network connection and API settings.
            </div>
            ${retryButton}
        </div>
    `;
    
    $(`#${elementId}`).html(html);
    
    // Add retry functionality if a function was provided
    if (retryFunc) {
        $(`#${elementId} .retry-btn`).on('click', function() {
            retryFunc();
        });
    }
}

// Get meaningful error message from API error
function getApiErrorMessage(xhr, status, error) {
    let errorMessage = 'Failed to load data from server.';
    
    if (xhr.responseJSON && xhr.responseJSON.error) {
        errorMessage = xhr.responseJSON.error;
    } else if (status === 'timeout') {
        errorMessage = 'Request timed out. Server might be under heavy load.';
    } else if (xhr.status === 0) {
        errorMessage = 'Cannot connect to server. Please check your network connection.';
    } else if (xhr.status === 401) {
        errorMessage = 'Session expired. Please login again.';
        // Redirect to login after showing message
        setTimeout(() => { window.location.href = '/login'; }, 3000);
    } else if (xhr.status === 403) {
        errorMessage = 'You do not have permission to access this resource.';
    } else if (xhr.status === 404) {
        errorMessage = 'Resource not found. The API endpoint may have changed.';
    } else if (xhr.status >= 500) {
        errorMessage = `Server error (${xhr.status}). Please try again later or contact support.`;
    }
    
    return errorMessage;
}

// Initialize dashboard data loading with retries
function initDashboardDataLoading() {
    // Define dashboard data elements to load
    const dashboardElements = [
        {
            url: '/api/status',
            elementId: 'lockStatusContainer',
            processor: function(data) {
                renderLockStatus(data);
            }
        },
        {
            url: '/api/activity?limit=5',
            elementId: 'recentActivityContainer',
            processor: function(data) {
                renderRecentActivity(data);
            }
        },
        {
            url: '/api/stats',
            elementId: 'statsContainer',
            processor: function(data) {
                renderStats(data);
            }
        }
    ];
    
    // Load each element
    dashboardElements.forEach(element => {
        fetchApiData(element.url, element.elementId, element.processor);
    });
    
    // Setup periodic refresh
    setInterval(() => {
        dashboardElements.forEach(element => {
            fetchApiData(element.url, element.elementId, element.processor, 'GET', null, 1, 1000);
        });
    }, 60000); // Refresh every minute
}

// Render lock status
function renderLockStatus(data) {
    if (!data || data.length === 0) {
        $('#lockStatusContainer').html(`
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                No smart locks found.
            </div>
        `);
        return;
    }
    
    let html = '<div class="row">';
    
    data.forEach(lock => {
        const stateClass = lock.state === 'locked' ? 'text-success' : 'text-danger';
        const stateIcon = lock.state === 'locked' ? 'fa-lock' : 'fa-lock-open';
        const batteryIcon = lock.battery_critical ? 'text-danger' : 'text-success';
        const lastActivity = lock.last_activity ? lock.last_activity : 'Unknown';
        const lastUser = lock.last_user ? lock.last_user : 'Unknown';
        
        html += `
            <div class="col-md-6 mb-4">
                <div class="card h-100">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">
                            <i class="fas fa-door-closed me-2"></i>${lock.name}
                        </h5>
                        <span class="badge ${stateClass}">
                            <i class="fas ${stateIcon} me-1"></i>${lock.state}
                        </span>
                    </div>
                    <div class="card-body">
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                <span><i class="fas fa-battery-full me-2 ${batteryIcon}"></i>Battery</span>
                                <span>${lock.battery_critical ? 'Critical' : 'Good'}</span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                <span><i class="fas fa-history me-2"></i>Last Activity</span>
                                <span>${lastActivity}</span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                <span><i class="fas fa-user me-2"></i>Last User</span>
                                <span>${lastUser}</span>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    $('#lockStatusContainer').html(html);
}

// Render recent activity
function renderRecentActivity(data) {
    if (!data || data.length === 0) {
        $('#recentActivityContainer').html(`
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                No recent activity found.
            </div>
        `);
        return;
    }
    
    let html = `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Lock</th>
                        <th>Action</th>
                        <th>User</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    data.forEach(activity => {
        const date = new Date(activity.date);
        const formattedDate = date.toLocaleString();
        
        html += `
            <tr>
                <td>${formattedDate}</td>
                <td>${activity.lock_name}</td>
                <td>${activity.action}</td>
                <td>${activity.user}</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    $('#recentActivityContainer').html(html);
}

// Render stats
function renderStats(data) {
    if (!data) {
        $('#statsContainer').html(`
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                No statistics available.
            </div>
        `);
        return;
    }
    
    let html = `
        <div class="row">
            <div class="col-md-6 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-users me-2"></i>Users</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="userChart" width="400" height="300"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-6 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-chart-pie me-2"></i>Actions</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="actionChart" width="400" height="300"></canvas>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    $('#statsContainer').html(html);
    
    // Initialize charts
    initializeUserChart(data.by_user);
    initializeActionChart(data.by_action);
}

// Initialize user chart
function initializeUserChart(userData) {
    if (!userData || userData.length === 0) return;
    
    const ctx = document.getElementById('userChart').getContext('2d');
    const labels = userData.map(item => item.name);
    const values = userData.map(item => item.count);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Actions by User',
                data: values,
                backgroundColor: 'rgba(54, 162, 235, 0.5)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

// Initialize action chart
function initializeActionChart(actionData) {
    if (!actionData || actionData.length === 0) return;
    
    const ctx = document.getElementById('actionChart').getContext('2d');
    const labels = actionData.map(item => item.name);
    const values = actionData.map(item => item.count);
    
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                label: 'Actions',
                data: values,
                backgroundColor: [
                    'rgba(255, 99, 132, 0.5)',
                    'rgba(54, 162, 235, 0.5)',
                    'rgba(255, 206, 86, 0.5)',
                    'rgba(75, 192, 192, 0.5)',
                    'rgba(153, 102, 255, 0.5)',
                    'rgba(255, 159, 64, 0.5)'
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)'
                ],
                borderWidth: 1
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
}

// Document ready handler
$(document).ready(function() {
    // Initialize dashboard data loading if on dashboard page
    if ($('#lockStatusContainer, #recentActivityContainer, #statsContainer').length > 0) {
        initDashboardDataLoading();
    }
    
    // Initialize activity page if on activity page
    if ($('#activityContainer').length > 0) {
        fetchApiData('/api/activity', 'activityContainer', function(data) {
            renderActivity(data);
        });
    }
    
    // Initialize users page if on users page
    if ($('#usersContainer').length > 0) {
        fetchApiData('/api/users', 'usersContainer', function(data) {
            renderUsers(data);
        });
    }
});
