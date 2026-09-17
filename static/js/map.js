/* Mapa Leaflet + OpenStreetMap: muestra las empresas encontradas como marcadores. */
const ProspectorMap = (() => {
    let map = null;
    let markersLayer = null;

    function init() {
        map = L.map("map").setView([4.7110, -74.0721], 10); // Bogota
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "&copy; colaboradores de OpenStreetMap",
        }).addTo(map);
        markersLayer = L.layerGroup().addTo(map);
    }

    function render(companies, onView) {
        if (!map) return;
        markersLayer.clearLayers();

        const withCoords = companies.filter(
            (c) => c.latitude != null && c.longitude != null
        );

        withCoords.forEach((company) => {
            const marker = L.marker([company.latitude, company.longitude]);

            const popupContent = document.createElement("div");
            popupContent.innerHTML = `
                <div class="fw-semibold mb-1">${Prospector.escapeHtml(company.name)}</div>
                <div class="small text-muted mb-1">${Prospector.escapeHtml(company.city || "")}</div>
                <div class="small mb-2">${Prospector.escapeHtml(company.category || "")}</div>
            `;
            const viewButton = document.createElement("button");
            viewButton.className = "btn btn-sm btn-primary";
            viewButton.textContent = "Ver";
            viewButton.addEventListener("click", () => onView(company.id));
            popupContent.appendChild(viewButton);

            marker.bindPopup(popupContent);
            markersLayer.addLayer(marker);
        });

        if (withCoords.length > 0) {
            const bounds = L.latLngBounds(withCoords.map((c) => [c.latitude, c.longitude]));
            map.fitBounds(bounds.pad(0.2));
        }
    }

    return { init, render };
})();
