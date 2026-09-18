/* Logica del dashboard: metadata, stats, busqueda, tabla+filtros, mapa y modales. */
(() => {
    const state = { meta: null, companiesById: {}, categoryLabels: {} };

    const alertBox = () => document.getElementById("dashboardAlert");

    async function loadMeta() {
        const res = await Prospector.apiRequest("/api/meta");
        state.meta = res.data;
        state.categoryLabels = Object.fromEntries(
            state.meta.categories.map((c) => [c.value, c.label])
        );

        document.getElementById("zoneCheckboxes").innerHTML = state.meta.zones
            .map(
                (zone) => `
            <div class="form-check">
                <input class="form-check-input" type="checkbox" value="${Prospector.escapeHtml(zone)}" id="zone-${Prospector.escapeHtml(zone)}" name="zone">
                <label class="form-check-label" for="zone-${Prospector.escapeHtml(zone)}">${Prospector.escapeHtml(zone)}</label>
            </div>`
            )
            .join("");

        document.getElementById("categoryCheckboxes").innerHTML = state.meta.categories
            .map(
                (cat) => `
            <div class="form-check">
                <input class="form-check-input" type="checkbox" value="${cat.value}" id="cat-${cat.value}" name="category">
                <label class="form-check-label" for="cat-${cat.value}">${Prospector.escapeHtml(cat.label)}</label>
            </div>`
            )
            .join("");

        const citySelect = document.getElementById("filterCity");
        const categorySelect = document.getElementById("filterCategory");
        const editCategorySelect = document.getElementById("editCategory");
        const statusSelect = document.getElementById("filterStatus");

        state.meta.zones.forEach((zone) => {
            citySelect.appendChild(new Option(zone, zone));
        });
        state.meta.categories.forEach((cat) => {
            categorySelect.appendChild(new Option(cat.label, cat.value));
            editCategorySelect.appendChild(new Option(cat.label, cat.value));
        });
        state.meta.statuses.forEach((s) => {
            statusSelect.appendChild(new Option(s.label, s.value));
        });
    }

    async function loadStats() {
        const res = await Prospector.apiRequest("/api/stats");
        Object.entries(res.data).forEach(([key, value]) => {
            const el = document.querySelector(`[data-stat="${key}"]`);
            if (el) el.textContent = value;
        });
    }

    function currentFilters() {
        const filters = {
            q: document.getElementById("filterQ").value.trim(),
            city: document.getElementById("filterCity").value,
            category: document.getElementById("filterCategory").value,
            status: document.getElementById("filterStatus").value,
        };
        if (document.getElementById("filterHasPhone").checked) filters.has_phone = "true";
        if (document.getElementById("filterHasWebsite").checked) filters.has_website = "true";
        return filters;
    }

    async function loadCompanies() {
        const params = new URLSearchParams();
        Object.entries(currentFilters()).forEach(([key, value]) => {
            if (value) params.set(key, value);
        });

        document.getElementById("exportButton").href = `/api/companies/export?${params.toString()}`;

        const res = await Prospector.apiRequest(`/api/companies?${params.toString()}`);
        const companies = res.data;
        state.companiesById = Object.fromEntries(companies.map((c) => [c.id, c]));
        renderTable(companies, params.toString().length > 0);
        ProspectorMap.render(companies, openCompanyModal);
    }

    function renderTable(companies, hasActiveFilters) {
        const tbody = document.getElementById("companiesTableBody");
        if (companies.length === 0) {
            const message = hasActiveFilters
                ? "No se encontraron empresas con estos filtros."
                : "Todavía no hay empresas. Usa el buscador para encontrar empresas.";
            tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted py-4">${message}</td></tr>`;
            return;
        }

        tbody.innerHTML = companies
            .map(
                (c) => `
            <tr>
                <td>${Prospector.escapeHtml(c.name)}</td>
                <td>${Prospector.escapeHtml(c.city || "-")}</td>
                <td>${Prospector.escapeHtml(state.categoryLabels[c.category] || c.category || "-")}</td>
                <td>${Prospector.escapeHtml(c.phone || "-")}</td>
                <td>${Prospector.escapeHtml(c.email || "-")}</td>
                <td>${c.website ? `<a href="${Prospector.escapeHtml(c.website)}" target="_blank" rel="noopener noreferrer">sitio</a>` : "-"}</td>
                <td>${c.prospect ? Prospector.statusBadgeHtml(c.prospect.status) : '<span class="text-muted small">Sin guardar</span>'}</td>
                <td class="text-end text-nowrap">
                    <button class="btn btn-sm btn-outline-secondary" data-action="view" data-id="${c.id}" title="Ver"><i class="bi bi-eye"></i></button>
                    <button class="btn btn-sm btn-outline-primary" data-action="save" data-id="${c.id}" title="Guardar" ${c.prospect ? "disabled" : ""}><i class="bi bi-bookmark-plus"></i></button>
                    <button class="btn btn-sm btn-outline-secondary" data-action="edit" data-id="${c.id}" title="Editar"><i class="bi bi-pencil"></i></button>
                </td>
            </tr>`
            )
            .join("");
    }

    function renderCompanyDetail(company) {
        const prospect = company.prospect;
        let gestionHtml;

        if (prospect) {
            const statusOptions = state.meta.statuses
                .map(
                    (s) =>
                        `<option value="${s.value}" ${s.value === prospect.status ? "selected" : ""}>${Prospector.escapeHtml(s.label)}</option>`
                )
                .join("");

            const notesHtml =
                (prospect.notes || [])
                    .map(
                        (n) => `
                <li class="list-group-item">
                    <div>${Prospector.escapeHtml(n.content)}</div>
                    <div class="small text-muted">${new Date(n.created_at).toLocaleString("es-CO")}</div>
                </li>`
                    )
                    .join("") ||
                '<li class="list-group-item text-muted">Sin notas todavía.</li>';

            gestionHtml = `
                <div class="mb-3">
                    <label class="form-label">Estado</label>
                    <select class="form-select" id="prospectStatusSelect" data-prospect-id="${prospect.id}">
                        ${statusOptions}
                    </select>
                </div>
                <ul class="list-group mb-3">${notesHtml}</ul>
                <form id="addNoteForm" data-prospect-id="${prospect.id}" class="d-flex gap-2">
                    <input type="text" class="form-control" id="noteContent" placeholder="Agregar nota comercial..." required>
                    <button type="submit" class="btn btn-outline-primary">Agregar</button>
                </form>`;
        } else {
            gestionHtml = `
                <p class="text-muted">Esta empresa aún no se ha guardado como prospecto.</p>
                <button class="btn btn-primary" id="saveAsProspectBtn" data-company-id="${company.id}">
                    <i class="bi bi-bookmark-plus"></i> Guardar como prospecto
                </button>`;
        }

        const findContactHtml = company.website
            ? `<button class="btn btn-sm btn-outline-secondary mb-2" id="findContactBtn" data-company-id="${company.id}">
                   <i class="bi bi-search"></i> Buscar contacto en su web
               </button>
               <div id="findContactResult" class="small mb-3"></div>`
            : "";

        const whatsappDigits = Prospector.toWhatsAppDigits(company.phone);
        const messageHtml = `
            <h6 class="text-uppercase text-muted small mt-4">Mensaje sugerido</h6>
            <p class="small text-muted mb-2">Bórralo o edítalo a tu gusto antes de abrirlo — el envío lo haces tú, desde tu propio correo o WhatsApp.</p>
            <textarea class="form-control mb-2" id="messageDraft" rows="4">${Prospector.escapeHtml(company.suggested_message || "")}</textarea>
            <div class="d-flex gap-2 mb-4">
                <button class="btn btn-sm btn-outline-primary" id="openEmailBtn" data-email="${Prospector.escapeHtml(company.email || "")}" ${company.email ? "" : "disabled"}>
                    <i class="bi bi-envelope"></i> Abrir en correo
                </button>
                <button class="btn btn-sm btn-outline-success" id="openWhatsappBtn" data-phone="${whatsappDigits || ""}" ${whatsappDigits ? "" : "disabled"}>
                    <i class="bi bi-whatsapp"></i> Abrir en WhatsApp
                </button>
            </div>
        `;

        return `
            <h6 class="text-uppercase text-muted small">Información</h6>
            <table class="table table-sm mb-3">
                <tbody>
                    <tr><th style="width:35%">Nombre</th><td>${Prospector.escapeHtml(company.name)}</td></tr>
                    <tr><th>Dirección</th><td>${Prospector.escapeHtml(company.address || "-")}</td></tr>
                    <tr><th>Ciudad</th><td>${Prospector.escapeHtml(company.city || "-")} ${company.department ? "(" + Prospector.escapeHtml(company.department) + ")" : ""}</td></tr>
                    <tr><th>Categoría</th><td>${Prospector.escapeHtml(state.categoryLabels[company.category] || company.category || "-")}</td></tr>
                    <tr><th>Teléfono</th><td>${Prospector.escapeHtml(company.phone || "-")}</td></tr>
                    <tr><th>Email</th><td>${Prospector.escapeHtml(company.email || "-")}</td></tr>
                    <tr><th>Website</th><td>${company.website ? `<a href="${Prospector.escapeHtml(company.website)}" target="_blank" rel="noopener noreferrer">${Prospector.escapeHtml(company.website)}</a>` : "-"}</td></tr>
                    <tr><th>Coordenadas</th><td>${company.latitude ?? "-"}, ${company.longitude ?? "-"}</td></tr>
                    <tr><th>Fuente</th><td>${Prospector.escapeHtml(company.source)}</td></tr>
                    <tr><th>Descubierta</th><td>${company.discovered_at ? new Date(company.discovered_at).toLocaleString("es-CO") : "-"}</td></tr>
                </tbody>
            </table>

            ${findContactHtml}
            ${messageHtml}

            <h6 class="text-uppercase text-muted small">Gestión comercial</h6>
            ${gestionHtml}
        `;
    }

    function wireCompanyModalEvents(company) {
        const saveBtn = document.getElementById("saveAsProspectBtn");
        if (saveBtn) {
            saveBtn.addEventListener("click", async () => {
                try {
                    await Prospector.apiRequest(`/api/companies/${company.id}/save`, { method: "POST" });
                    await openCompanyModal(company.id);
                    await Promise.all([loadCompanies(), loadStats()]);
                } catch (err) {
                    Prospector.showAlert(alertBox(), err.message);
                }
            });
        }

        const statusSelect = document.getElementById("prospectStatusSelect");
        if (statusSelect) {
            statusSelect.addEventListener("change", async (e) => {
                try {
                    await Prospector.apiRequest(`/api/prospects/${e.target.dataset.prospectId}`, {
                        method: "PUT",
                        body: JSON.stringify({ status: e.target.value }),
                    });
                    await Promise.all([loadCompanies(), loadStats()]);
                } catch (err) {
                    Prospector.showAlert(alertBox(), err.message);
                }
            });
        }

        const noteForm = document.getElementById("addNoteForm");
        if (noteForm) {
            noteForm.addEventListener("submit", async (e) => {
                e.preventDefault();
                const input = document.getElementById("noteContent");
                try {
                    await Prospector.apiRequest(`/api/prospects/${e.target.dataset.prospectId}/notes`, {
                        method: "POST",
                        body: JSON.stringify({ content: input.value }),
                    });
                    await openCompanyModal(company.id);
                } catch (err) {
                    Prospector.showAlert(alertBox(), err.message);
                }
            });
        }

        const findContactBtn = document.getElementById("findContactBtn");
        if (findContactBtn) {
            findContactBtn.addEventListener("click", async () => {
                const resultBox = document.getElementById("findContactResult");
                findContactBtn.disabled = true;
                resultBox.innerHTML = '<span class="text-muted">Buscando en su sitio web...</span>';
                try {
                    const res = await Prospector.apiRequest(`/api/companies/${company.id}/find-contact`, {
                        method: "POST",
                    });
                    const found = res.data.found;
                    if (found.email || found.whatsapp_phone) {
                        await openCompanyModal(company.id);
                        await loadCompanies();
                    } else {
                        resultBox.innerHTML =
                            '<span class="text-muted">No se encontró email ni WhatsApp visible en su sitio web.</span>';
                        findContactBtn.disabled = false;
                    }
                } catch (err) {
                    resultBox.innerHTML = `<span class="text-danger">${Prospector.escapeHtml(err.message)}</span>`;
                    findContactBtn.disabled = false;
                }
            });
        }

        const openEmailBtn = document.getElementById("openEmailBtn");
        if (openEmailBtn && !openEmailBtn.disabled) {
            openEmailBtn.addEventListener("click", () => {
                const message = document.getElementById("messageDraft").value;
                const subject = encodeURIComponent(`Servicios de cargue y descargue - ${company.name}`);
                window.location.href = `mailto:${openEmailBtn.dataset.email}?subject=${subject}&body=${encodeURIComponent(message)}`;
            });
        }

        const openWhatsappBtn = document.getElementById("openWhatsappBtn");
        if (openWhatsappBtn && !openWhatsappBtn.disabled) {
            openWhatsappBtn.addEventListener("click", () => {
                const message = document.getElementById("messageDraft").value;
                window.open(
                    `https://wa.me/${openWhatsappBtn.dataset.phone}?text=${encodeURIComponent(message)}`,
                    "_blank"
                );
            });
        }
    }

    async function openCompanyModal(id) {
        const modalTitle = document.getElementById("companyModalTitle");
        const modalBody = document.getElementById("companyModalBody");
        modalBody.innerHTML = '<div class="text-center text-muted py-4">Cargando...</div>';
        bootstrap.Modal.getOrCreateInstance(document.getElementById("companyModal")).show();

        try {
            const res = await Prospector.apiRequest(`/api/companies/${id}`);
            const company = res.data;
            modalTitle.textContent = company.name;
            modalBody.innerHTML = renderCompanyDetail(company);
            wireCompanyModalEvents(company);
        } catch (err) {
            modalBody.innerHTML = `<div class="alert alert-danger">${Prospector.escapeHtml(err.message)}</div>`;
        }
    }

    function openEditModal(company) {
        document.getElementById("editCompanyId").value = company.id;
        document.getElementById("editName").value = company.name || "";
        document.getElementById("editAddress").value = company.address || "";
        document.getElementById("editCity").value = company.city || "";
        document.getElementById("editDepartment").value = company.department || "";
        document.getElementById("editPhone").value = company.phone || "";
        document.getElementById("editEmail").value = company.email || "";
        document.getElementById("editWebsite").value = company.website || "";
        document.getElementById("editCategory").value = company.category || "";
        document.getElementById("editDescription").value = company.description || "";

        bootstrap.Modal.getOrCreateInstance(document.getElementById("editModal")).show();
    }

    async function saveCompanyAsProspect(id) {
        try {
            await Prospector.apiRequest(`/api/companies/${id}/save`, { method: "POST" });
            await Promise.all([loadCompanies(), loadStats()]);
        } catch (err) {
            Prospector.showAlert(alertBox(), err.message);
        }
    }

    async function cleanupChains() {
        const button = document.getElementById("cleanupChainsButton");
        button.disabled = true;
        try {
            const res = await Prospector.apiRequest("/api/companies/cleanup-chains", { method: "POST" });
            Prospector.showAlert(
                alertBox(),
                `Se quitaron ${res.data.removed} empresas de cadenas/franquicias con muchas ubicaciones.`,
                "success"
            );
            await Promise.all([loadCompanies(), loadStats()]);
        } catch (err) {
            Prospector.showAlert(alertBox(), err.message);
        } finally {
            button.disabled = false;
        }
    }

    function wireStaticEvents() {
        document.getElementById("companiesTableBody").addEventListener("click", (e) => {
            const btn = e.target.closest("button[data-action]");
            if (!btn) return;
            const id = Number(btn.dataset.id);

            if (btn.dataset.action === "view") openCompanyModal(id);
            else if (btn.dataset.action === "edit") {
                const company = state.companiesById[id];
                if (company) openEditModal(company);
            } else if (btn.dataset.action === "save") saveCompanyAsProspect(id);
        });

        document.getElementById("cleanupChainsButton").addEventListener("click", cleanupChains);

        ["filterCity", "filterCategory", "filterStatus", "filterHasPhone", "filterHasWebsite"].forEach(
            (id) => document.getElementById(id).addEventListener("change", loadCompanies)
        );

        let debounceTimer;
        document.getElementById("filterQ").addEventListener("input", () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(loadCompanies, 400);
        });

        document.getElementById("searchForm").addEventListener("submit", async (e) => {
            e.preventDefault();
            const zones = Array.from(document.querySelectorAll('input[name="zone"]:checked')).map((el) => el.value);
            const categories = Array.from(document.querySelectorAll('input[name="category"]:checked')).map((el) => el.value);

            alertBox().innerHTML = "";
            if (zones.length === 0 || categories.length === 0) {
                Prospector.showAlert(alertBox(), "Selecciona al menos una zona y una categoría.", "warning");
                return;
            }

            const button = document.getElementById("searchButton");
            const spinner = document.getElementById("searchSpinner");
            button.disabled = true;
            spinner.classList.remove("d-none");

            try {
                const res = await Prospector.apiRequest("/api/search", {
                    method: "POST",
                    body: JSON.stringify({ zones, categories }),
                });
                const { found, created, updated, skipped_chains } = res.data;
                const chainsMsg = skipped_chains
                    ? ` Se excluyeron ${skipped_chains} por ser sucursales de una cadena/franquicia.`
                    : "";
                Prospector.showAlert(
                    alertBox(),
                    `Búsqueda completada: ${found} empresas encontradas (${created} nuevas, ${updated} actualizadas).${chainsMsg}`,
                    "success"
                );
                await Promise.all([loadCompanies(), loadStats()]);
            } catch (err) {
                Prospector.showAlert(alertBox(), err.message);
            } finally {
                button.disabled = false;
                spinner.classList.add("d-none");
            }
        });

        document.getElementById("editForm").addEventListener("submit", async (e) => {
            e.preventDefault();
            const id = document.getElementById("editCompanyId").value;
            const payload = {
                name: document.getElementById("editName").value,
                address: document.getElementById("editAddress").value,
                city: document.getElementById("editCity").value,
                department: document.getElementById("editDepartment").value,
                phone: document.getElementById("editPhone").value,
                email: document.getElementById("editEmail").value,
                website: document.getElementById("editWebsite").value,
                category: document.getElementById("editCategory").value,
                description: document.getElementById("editDescription").value,
            };

            try {
                await Prospector.apiRequest(`/api/companies/${id}`, {
                    method: "PUT",
                    body: JSON.stringify(payload),
                });
                bootstrap.Modal.getInstance(document.getElementById("editModal")).hide();
                await Promise.all([loadCompanies(), loadStats()]);
            } catch (err) {
                Prospector.showAlert(alertBox(), err.message);
            }
        });
    }

    async function init() {
        ProspectorMap.init();
        wireStaticEvents();
        try {
            await loadMeta();
            await Promise.all([loadStats(), loadCompanies()]);
        } catch (err) {
            Prospector.showAlert(alertBox(), err.message);
        }
    }

    init();
})();
