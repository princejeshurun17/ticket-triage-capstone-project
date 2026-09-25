let globalStatuses = [];

document.addEventListener('DOMContentLoaded', async () => {
    // Determine which page we are on
    const isAdmin = document.getElementById('admin-dashboard') !== null;
    const isSubmit = document.getElementById('ticket-form') !== null;

    if (isSubmit || isAdmin) {
        await loadReferenceData(isAdmin, isSubmit);
    }

    if (isSubmit) {
        document.getElementById('ticket-form').addEventListener('submit', submitTicket);
    }

    if (isAdmin) {
        loadTickets();
    }
});

async function loadReferenceData(isAdmin, isSubmit) {
    try {
        const res = await fetch('/api/categories');
        const data = await res.json();
        globalStatuses = data.statuses;

        if (isSubmit) {
            populateSelect('category', data.categories, '-- Auto-suggest --');
            populateSelect('priority', data.priorities, '-- Optional --');
        }

        if (isAdmin) {
            populateSelect('filter-category', data.categories, 'All Categories');
            populateSelect('filter-status', data.statuses, 'All Statuses');
        }
    } catch (err) {
        console.error("Failed to load API reference data. Ensure backend is running.", err);
    }
}

function populateSelect(elementId, options, defaultText) {
    const select = document.getElementById(elementId);
    if (!select) return;
    
    select.innerHTML = `<option value="">${defaultText}</option>`;
    options.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt;
        option.textContent = opt;
        select.appendChild(option);
    });
}

// --- Submit Logic (index.html) ---
async function submitTicket(e) {
    e.preventDefault();
    const msgDiv = document.getElementById('submit-message');
    const submitBtn = e.target.querySelector('button[type="submit"]');
    
    submitBtn.textContent = 'Submitting...';
    submitBtn.disabled = true;

    const payload = {
        name: document.getElementById('name').value,
        email: document.getElementById('email').value,
        title: document.getElementById('title').value,
        description: document.getElementById('description').value,
        priority: document.getElementById('priority').value || undefined,
        category: document.getElementById('category').value || undefined
    };

    try {
        const res = await fetch('/api/tickets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        msgDiv.classList.remove('hidden', 'msg-success', 'msg-error');

        if (res.ok) {
            const data = await res.json();
            msgDiv.classList.add('msg-success');
            msgDiv.innerHTML = `Ticket successfully created!<br>ID: <b>${data.id.substring(0,8)}...</b> | Suggested Category: <b>${data.category}</b>`;
            document.getElementById('ticket-form').reset();
        } else {
            const err = await res.json();
            msgDiv.classList.add('msg-error');
            msgDiv.innerHTML = `Error: ${err.error}`;
        }
    } catch (err) {
        msgDiv.classList.remove('hidden');
        msgDiv.classList.add('msg-error');
        msgDiv.innerHTML = `Network error. Please check your connection to the API.`;
    } finally {
        submitBtn.textContent = 'Submit Request';
        submitBtn.disabled = false;
    }
}

// --- Admin Logic (admin.html) ---
async function loadTickets() {
    const category = document.getElementById('filter-category').value;
    const status = document.getElementById('filter-status').value;
    const search = document.getElementById('filter-search').value;

    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (status) params.append('status', status);
    if (search) params.append('search', search);

    try {
        const res = await fetch(`/api/tickets?${params.toString()}`);
        const data = await res.json();
        renderTicketsTable(data.tickets);
    } catch (err) {
        console.error("Failed to load tickets", err);
    }
}

function renderTicketsTable(tickets) {
    const tbody = document.getElementById('tickets-body');
    tbody.innerHTML = '';

    if (tickets.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 2rem;">No tickets found matching your criteria.</td></tr>`;
        return;
    }

    tickets.forEach(ticket => {
        const tr = document.createElement('tr');
        
        let statusOptions = globalStatuses.map(s => 
            `<option value="${s}" ${ticket.status === s ? 'selected' : ''}>${s}</option>`
        ).join('');

        tr.innerHTML = `
            <td>
                <p><strong>${ticket.title}</strong></p>
                <small>${ticket.description.length > 60 ? ticket.description.substring(0, 60) + '...' : ticket.description}</small>
            </td>
            <td>
                <p>${ticket.name}</p>
                <small>${ticket.email}</small>
            </td>
            <td><span style="background:#E5E7EB; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem;">${ticket.category}</span></td>
            <td>
                <select id="status-${ticket.id}" class="status-select">
                    ${statusOptions}
                </select>
            </td>
            <td>
                <button onclick="updateTicketStatus('${ticket.id}')" class="btn btn-primary btn-sm">Save</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function updateTicketStatus(id) {
    const newStatus = document.getElementById(`status-${id}`).value;
    const adminKey = document.getElementById('admin-key').value;

    const headers = { 'Content-Type': 'application/json' };
    if (adminKey) {
        headers['x-admin-key'] = adminKey;
    }

    try {
        const res = await fetch(`/api/tickets/${id}`, {
            method: 'PATCH',
            headers: headers,
            body: JSON.stringify({ status: newStatus })
        });

        if (res.ok) {
            alert('Status successfully updated.');
            loadTickets(); // Refresh table
        } else {
            const err = await res.json();
            alert(`Update failed: ${err.error || 'Unauthorized'}`);
        }
    } catch (err) {
        alert('Network error occurred while updating.');
    }
}