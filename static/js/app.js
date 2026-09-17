/* Utilidades compartidas: llamadas a la API y helpers de presentacion. */
const Prospector = (() => {
    async function apiRequest(url, options = {}) {
        const response = await fetch(url, {
            headers: { "Content-Type": "application/json" },
            ...options,
        });

        let body = null;
        try {
            body = await response.json();
        } catch (err) {
            body = null;
        }

        if (!response.ok) {
            const message =
                (body && body.error) || "Ocurrio un error inesperado. Intenta nuevamente.";
            throw new Error(message);
        }

        return body;
    }

    const OPPORTUNITY_INFO = {
        alta: { label: "Alta oportunidad", className: "badge-opportunity-alta", icon: "bi-arrow-up-circle-fill" },
        media: { label: "Oportunidad media", className: "badge-opportunity-media", icon: "bi-dash-circle-fill" },
        baja: { label: "Baja oportunidad", className: "badge-opportunity-baja", icon: "bi-arrow-down-circle-fill" },
    };

    const STATUS_INFO = {
        new: { label: "Sin contactar", className: "badge-status-new" },
        contacted: { label: "Contactado", className: "badge-status-active" },
        responded: { label: "Respondió", className: "badge-status-active" },
        interested: { label: "Interesado", className: "badge-status-active" },
        quote_sent: { label: "Cotización enviada", className: "badge-status-active" },
        customer: { label: "Cliente", className: "badge-status-customer" },
        not_interested: { label: "No interesado", className: "badge-status-inactive" },
    };

    function escapeHtml(value) {
        const div = document.createElement("div");
        div.textContent = value == null ? "" : String(value);
        return div.innerHTML;
    }

    function opportunityBadgeHtml(level) {
        const info = OPPORTUNITY_INFO[level] || OPPORTUNITY_INFO.baja;
        return `<span class="badge-opportunity ${info.className}"><i class="bi ${info.icon}"></i> ${info.label}</span>`;
    }

    function statusBadgeHtml(status) {
        const info = STATUS_INFO[status] || STATUS_INFO.new;
        return `<span class="badge-status ${info.className}">${info.label}</span>`;
    }

    function showAlert(container, message, type = "danger") {
        container.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${escapeHtml(message)}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Cerrar"></button>
            </div>`;
    }

    return {
        apiRequest,
        opportunityBadgeHtml,
        statusBadgeHtml,
        showAlert,
        escapeHtml,
        OPPORTUNITY_INFO,
        STATUS_INFO,
    };
})();
