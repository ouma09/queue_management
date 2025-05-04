// Connect to Socket.IO server
const socket = io();

// DOM Elements
const queueTable = document.getElementById('queueTable');
const waitingCount = document.getElementById('waitingCount');
const avgWaitTime = document.getElementById('avgWaitTime');
const todayClients = document.getElementById('todayClients');

// Add these variables at the top of your JavaScript
let currentlyCalledClient = null;

// Format phone number
function formatPhone(phone) {
    return phone.replace(/(\+212)(\d{2})(\d{4})(\d{4})/, '$1 $2 $3 $4');
}

// Format wait time
function formatWaitTime(minutes) {
    if (minutes < 60) {
        return `${minutes} min`;
    }
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
}

// Load queue data
function loadQueue() {
    fetch('/api/queue')
        .then(response => response.json())
        .then(clients => {
            // Clear table
            queueTable.innerHTML = '';
            
            // Update stats
            const waitingClients = clients.filter(c => c.status === 'waiting');
            waitingCount.textContent = waitingClients.length;
            
            if (waitingClients.length > 0) {
                const totalWaitTime = waitingClients.reduce((sum, c) => sum + c.wait_time, 0);
                const avg = Math.round(totalWaitTime / waitingClients.length);
                avgWaitTime.textContent = formatWaitTime(avg);
            } else {
                avgWaitTime.textContent = '0 min';
            }
            
            todayClients.textContent = clients.length;
            
            // Add clients to table
            clients.forEach(client => {
                const row = document.createElement('tr');
                
                // Format status display
                const statusClass = `status-${client.status}`;
                
                row.innerHTML = `
                    <td>${client.position}</td>
                    <td>${client.name}</td>
                    <td>${formatPhone(client.phone_number)}</td>
                    <td>${client.service_type}</td>
                    <td>${formatWaitTime(client.wait_time)}</td>
                    <td class="${statusClass}">${client.status.toUpperCase()}</td>
                    <td>
                        ${client.status === 'waiting' ? 
                            `<button class="call-btn" onclick="callClient(${client.id})">Call</button>` : ''}
                        ${client.status === 'called' ? 
                            `<button class="complete-btn" onclick="completeService(${client.id})">Complete</button>` : ''}
                    </td>
                `;
                
                queueTable.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Error loading queue:', error);
        });
}

function updateQueueList(clients) {
    const queueList = document.getElementById('queue-list');
    queueList.innerHTML = '';
    
    // Trouver le client actuellement appelé
    currentlyCalledClient = clients.find(client => 
        client.status === 'called' || client.status === 'in_service'
    )?.id || null;
    
    clients.forEach(client => {
        const clientCard = createClientCard(client);
        queueList.appendChild(clientCard);
    });
    
    updateStatistics(clients);
}

function createClientCard(client) {
    const card = document.createElement('div');
    card.className = 'card mb-2 queue-card';
    
    // Déterminer si le bouton d'appel doit être désactivé
    const isCallDisabled = currentlyCalledClient !== null && client.status === 'waiting';
    const callButtonClass = isCallDisabled ? 'btn-secondary' : 'btn-primary';
    
    card.innerHTML = `
        <div class="card-body">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h5 class="card-title">Client #${client.id}</h5>
                    <p class="card-text">
                        <strong>Nom:</strong> ${client.name}<br>
                        <strong>Service:</strong> ${client.service_type}<br>
                        <strong>Position:</strong> ${client.position}<br>
                        <strong>Temps d'attente:</strong> ${client.wait_time} minutes
                    </p>
                    <p class="card-text">
                        <small class="text-muted">Statut: ${client.status.toUpperCase()}</small>
                    </p>
                </div>
                <div>
                    ${client.status === 'waiting' ? `
                        <button class="btn ${callButtonClass} btn-action" 
                                onclick="callClient(${client.id})"
                                ${isCallDisabled ? 'disabled' : ''}>
                            <i class="fas fa-phone me-1"></i> Appeler
                        </button>
                    ` : ''}
                    ${client.status === 'called' ? `
                        <button class="btn btn-success btn-action" onclick="startService(${client.id})">
                            <i class="fas fa-play me-1"></i> Démarrer
                        </button>
                    ` : ''}
                </div>
            </div>
        </div>
    `;
    return card;
}

// Fonction pour afficher les notifications
function showNotification(message, type = 'info') {
    // Créer l'élément de notification
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '1000';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Ajouter la notification au body
    document.body.appendChild(notification);
    
    // Supprimer la notification après 5 secondes
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

function callClient(clientId) {
    if (currentlyCalledClient) {
        showNotification(
            '⚠️ Impossible d\'appeler un nouveau client. Vous avez déjà un client en cours d\'appel. Veuillez terminer ou annuler le service en cours avant d\'appeler un nouveau client.',
            'warning'
        );
        return;
    }
    
    fetch(`/api/call_client/${clientId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentlyCalledClient = clientId;
            showNotification('✅ Client appelé avec succès', 'success');
            updateQueue();
        } else {
            showNotification(`❌ ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        showNotification('❌ Erreur lors de l\'appel du client', 'danger');
    });
}

// Add function to handle completing service
function completeService(clientId) {
    // Disable the button to prevent double clicks
    const button = document.querySelector(`button[onclick="completeService(${clientId})"]`);
    if (button) {
        button.disabled = true;
    }

    fetch(`/api/complete_service/${clientId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentlyCalledClient = null;
            showNotification(data.message || 'Service completed successfully', 'success');
            updateQueue();
        } else {
            showNotification(data.message || 'Error completing service', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error completing service', 'danger');
    })
    .finally(() => {
        // Re-enable the button after a short delay
        if (button) {
            setTimeout(() => {
                button.disabled = false;
            }, 2000);
        }
    });
}

// Add function to handle service cancellation
function cancelService(clientId) {
    fetch(`/api/cancel_service/${clientId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentlyCalledClient = null;
            showNotification('Service cancelled successfully', 'info');
            updateQueue();
        } else {
            showNotification(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error cancelling service', 'error');
    });
}

// Socket.IO events
socket.on('connect', () => {
    console.log('Connected to server');
    loadQueue();
});

socket.on('queue_update', (data) => {
    if (data.action === 'client_called') {
        currentlyCalledClient = data.client_id;
    } else if (data.action === 'service_completed' || data.action === 'service_cancelled') {
        currentlyCalledClient = null;
    }
    updateQueue();
});

// Initial load
document.addEventListener('DOMContentLoaded', loadQueue);

// Refresh every 30 seconds
setInterval(loadQueue, 30000);

// Ajouter des styles pour les notifications
const style = document.createElement('style');
style.textContent = `
    .alert {
        padding: 15px;
        margin-bottom: 20px;
        border: 1px solid transparent;
        border-radius: 4px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .alert-success {
        color: #155724;
        background-color: #d4edda;
        border-color: #c3e6cb;
    }
    .alert-warning {
        color: #856404;
        background-color: #fff3cd;
        border-color: #ffeeba;
    }
    .alert-danger {
        color: #721c24;
        background-color: #f8d7da;
        border-color: #f5c6cb;
    }
    .alert-info {
        color: #0c5460;
        background-color: #d1ecf1;
        border-color: #bee5eb;
    }
`;
document.head.appendChild(style); 