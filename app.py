from flask import Flask, jsonify, render_template_string, request
import json
import os

app = Flask(__name__)

BASE = os.path.dirname(__file__)

_cache = {}

def load_geojson(path):
    if path not in _cache:
        with open(os.path.join(BASE, path)) as f:
            _cache[path] = json.load(f)
    return _cache[path]


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Data Centre Heatmap</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
        #map { width: 100vw; height: 100vh; }

        .info-panel {
            position: absolute;
            top: 15px;
            left: 55px;
            z-index: 1000;
            background: white;
            border-radius: 12px;
            padding: 12px 20px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.15);
        }
        .info-panel h1 {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 4px;
        }
        .info-panel p {
            font-size: 12px;
            color: #666;
        }

        .legend {
            position: absolute;
            bottom: 30px;
            left: 55px;
            z-index: 1000;
            background: white;
            border-radius: 12px;
            padding: 12px 16px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.15);
        }
        .legend h3 { font-size: 13px; margin-bottom: 8px; }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            margin-bottom: 4px;
        }
        .legend-color {
            width: 20px;
            height: 14px;
            border-radius: 2px;
            border: 1px solid rgba(0,0,0,0.1);
        }

        .hover-info {
            position: absolute;
            top: 15px;
            right: 15px;
            z-index: 1000;
            background: white;
            border-radius: 12px;
            padding: 12px 20px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.15);
            min-width: 220px;
            display: none;
        }
        .hover-info h3 { font-size: 14px; margin-bottom: 4px; }
        .hover-info .county-name { font-size: 11px; color: #999; margin-bottom: 6px; }
        .hover-info .score { font-size: 28px; font-weight: 700; }
        .hover-info .label { font-size: 12px; color: #666; }
        .hover-info .details { font-size: 12px; color: #444; margin-top: 8px; line-height: 1.6; }

        .loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 2000;
            background: white;
            border-radius: 12px;
            padding: 20px 30px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.15);
            font-size: 14px;
        }

        .toggles {
            position: absolute;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1000;
            background: white;
            border-radius: 12px;
            padding: 10px 16px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.15);
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            justify-content: center;
        }
        .toggle-btn {
            padding: 6px 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            background: white;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.15s;
            font-family: inherit;
        }
        .toggle-btn.active {
            border-color: #333;
            background: #333;
            color: white;
        }
        .toggle-btn:hover {
            border-color: #999;
        }
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="loading" id="loading">Loading map data...</div>

    <div class="info-panel">
        <h1>Data Centre Suitability</h1>
        <p>Heatmap of the USA by county &mdash; hover for details</p>
    </div>

    <div class="legend">
        <h3>Suitability Score</h3>
        <div class="legend-item"><div class="legend-color" style="background:#1a9641"></div> Excellent (80-100)</div>
        <div class="legend-item"><div class="legend-color" style="background:#a6d96a"></div> Good (60-80)</div>
        <div class="legend-item"><div class="legend-color" style="background:#ffffbf"></div> Moderate (40-60)</div>
        <div class="legend-item"><div class="legend-color" style="background:#fdae61"></div> Below avg (20-40)</div>
        <div class="legend-item"><div class="legend-color" style="background:#d7191c"></div> Poor (0-20)</div>
    </div>

    <div class="toggles" id="toggles">
        <button class="toggle-btn active" data-layer="power">Power Price</button>
        <button class="toggle-btn active" data-layer="land">Land Cost</button>
        <button class="toggle-btn active" data-layer="permits">Permits</button>
        <button class="toggle-btn active" data-layer="reg">Regulation</button>
        <button class="toggle-btn active" data-layer="broadband">Broadband</button>
        <button class="toggle-btn active" data-layer="transmission">Transmission Lines</button>
    </div>

    <div class="hover-info" id="hover-info">
        <h3 id="hover-loc"></h3>
        <div class="county-name" id="hover-county"></div>
        <div class="score" id="hover-score"></div>
        <div class="label" id="hover-label"></div>
        <div class="details" id="hover-details"></div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const map = L.map('map', {
            center: [39.0, -96.0],
            zoom: 5,
            zoomControl: false,
            maxBounds: [[24, -130], [50, -65]],
            maxBoundsViscosity: 1.0,
            minZoom: 4
        });

        L.control.zoom({ position: 'bottomright' }).addTo(map);

        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; OpenStreetMap &copy; CARTO',
            maxZoom: 19
        }).addTo(map);

        // Layer definitions: key -> { scoreField, label, format }
        const LAYERS = {
            power:     { field: 's_power',     label: 'Power',              fmt: p => p.power_price != null ? p.power_price + ' ¢/kWh' : 'n/a' },
            land:      { field: 's_land',      label: 'Land cost',          fmt: p => p.home_value != null ? '$' + p.home_value.toLocaleString() : 'n/a' },
            permits:   { field: 's_permits',   label: 'Permits/1k pop',     fmt: p => p.permits_pc != null ? '' + p.permits_pc : 'n/a' },
            reg:       { field: 's_reg',       label: 'Regulatory freedom', fmt: p => p.reg_freedom != null ? '' + p.reg_freedom : 'n/a' },
            broadband: { field: 's_broadband', label: 'Broadband tier',     fmt: p => p.broadband_tier != null ? p.broadband_tier + '/5' : 'n/a' }
        };

        // Track which layers are active
        const activeLayers = { power: true, land: true, permits: true, reg: true, broadband: true, transmission: true };

        function computeScore(props) {
            let total = 0, count = 0;
            for (const [key, cfg] of Object.entries(LAYERS)) {
                if (!activeLayers[key]) continue;
                const val = props[cfg.field];
                if (val != null) {
                    total += val;
                    count++;
                }
            }
            return count > 0 ? Math.round(total / count * 10) / 10 : 50;
        }

        function scoreToColor(score) {
            if (score >= 80) return '#1a9641';
            if (score >= 65) return '#a6d96a';
            if (score >= 50) return '#ffffbf';
            if (score >= 35) return '#fdae61';
            if (score >= 20) return '#f46d43';
            return '#d7191c';
        }

        function scoreToLabel(score) {
            if (score >= 80) return 'Excellent';
            if (score >= 65) return 'Good';
            if (score >= 50) return 'Moderate';
            if (score >= 35) return 'Below Average';
            if (score >= 20) return 'Poor';
            return 'Very Poor';
        }

        function scoreToOpacity(score) {
            const dist = Math.abs(score - 50) / 50;
            return 0.4 + dist * 0.35;
        }

        const hoverInfo = document.getElementById('hover-info');
        const hoverScore = document.getElementById('hover-score');
        const hoverLabel = document.getElementById('hover-label');
        const hoverLoc = document.getElementById('hover-loc');
        const hoverCounty = document.getElementById('hover-county');
        const hoverDetails = document.getElementById('hover-details');
        const loading = document.getElementById('loading');

        let activeHoverLayer = null;
        let countyLayer = null;
        let countyGeojsonData = null;

        function styleFeature(feature) {
            const score = computeScore(feature.properties);
            return {
                fillColor: scoreToColor(score),
                fillOpacity: scoreToOpacity(score),
                color: '#fff',
                weight: 0.5,
                opacity: 0.5
            };
        }

        function onFeatureHover(feature, layer) {
            layer.on('mouseover', function(e) {
                if (activeHoverLayer) {
                    activeHoverLayer.setStyle({ weight: 0.5, color: '#fff' });
                }
                this.setStyle({ weight: 2, color: '#333' });
                this.bringToFront();
                activeHoverLayer = this;

                const props = feature.properties;
                const score = computeScore(props);
                hoverInfo.style.display = 'block';
                hoverLoc.textContent = (props.NAME || '') + ' County';
                hoverCounty.textContent = 'FIPS: ' + (props.STATE||'') + (props.COUNTY||'');
                hoverScore.textContent = score + '/100';
                hoverScore.style.color = scoreToColor(score);
                hoverLabel.textContent = scoreToLabel(score);

                let lines = [];
                for (const [key, cfg] of Object.entries(LAYERS)) {
                    const active = activeLayers[key];
                    const prefix = active ? '' : '<span style="color:#bbb">';
                    const suffix = active ? '' : '</span>';
                    lines.push(prefix + cfg.label + ': ' + cfg.fmt(props) + suffix);
                }
                hoverDetails.innerHTML = lines.join('<br>');
            });
            layer.on('mouseout', function(e) {
                this.setStyle({ weight: 0.5, color: '#fff' });
                hoverInfo.style.display = 'none';
                activeHoverLayer = null;
            });
        }

        function refreshStyles() {
            if (!countyLayer) return;
            countyLayer.eachLayer(function(layer) {
                layer.setStyle(styleFeature(layer.feature));
            });
        }

        // Load counties
        fetch('/api/counties')
            .then(r => r.json())
            .then(geojson => {
                countyGeojsonData = geojson;
                countyLayer = L.geoJSON(geojson, {
                    style: styleFeature,
                    onEachFeature: onFeatureHover
                }).addTo(map);
                loading.style.display = 'none';
            });

        // Transmission lines overlay
        let transmissionLayer = null;

        function loadTransmission() {
            if (!activeLayers.transmission) return;
            const bounds = map.getBounds();
            const bbox = bounds.getWest() + ',' + bounds.getSouth() + ',' +
                         bounds.getEast() + ',' + bounds.getNorth();

            fetch('/api/transmission?bbox=' + bbox)
                .then(r => r.json())
                .then(geojson => {
                    if (transmissionLayer) {
                        map.removeLayer(transmissionLayer);
                    }
                    transmissionLayer = L.geoJSON(geojson, {
                        style: { color: '#ff6600', weight: 1.5, opacity: 0.5 },
                        onEachFeature: function(feature, layer) {
                            const p = feature.properties;
                            const tip = (p.volt_class || 'Unknown') + ' kV' +
                                (p.owner && p.owner !== 'NOT AVAILABLE' ? ' — ' + p.owner : '');
                            layer.bindTooltip(tip);
                        }
                    }).addTo(map);
                });
        }

        loadTransmission();

        // Toggle buttons
        document.querySelectorAll('.toggle-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const layer = this.dataset.layer;
                activeLayers[layer] = !activeLayers[layer];
                this.classList.toggle('active');

                if (layer === 'transmission') {
                    if (activeLayers.transmission) {
                        loadTransmission();
                    } else if (transmissionLayer) {
                        map.removeLayer(transmissionLayer);
                        transmissionLayer = null;
                    }
                } else {
                    refreshStyles();
                }
            });
        });

        // Hide layers while panning for performance, reload transmission on stop
        var pane = map.getPane('overlayPane');
        map.on('movestart', function() {
            pane.style.visibility = 'hidden';
        });
        map.on('moveend', function() {
            pane.style.visibility = 'visible';
            if (activeLayers.transmission) loadTransmission();
        });
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/counties")
def counties():
    return jsonify(load_geojson("counties_scored.geojson"))


@app.route("/api/fibre")
def fibre():
    return jsonify(load_geojson("data/fibre/fibre.geojson"))


_transmission = None

def get_transmission():
    global _transmission
    if _transmission is None:
        with open(os.path.join(BASE, "data/transmission_lines.geojson")) as f:
            _transmission = json.load(f)["features"]
    return _transmission


@app.route("/api/transmission")
def transmission():
    features = get_transmission()
    bbox = request.args.get("bbox")  # west,south,east,north

    # Filter to viewport if bbox provided
    if bbox:
        west, south, east, north = [float(x) for x in bbox.split(",")]
        visible = []
        for f in features:
            coords = f["geometry"]["coordinates"]
            if f["geometry"]["type"] == "MultiLineString":
                coords = coords[0]
            # Check if first coord is in bbox (fast approximate filter)
            if coords:
                lon, lat = coords[0]
                if west <= lon <= east and south <= lat <= north:
                    visible.append(f)
        features = visible

    # Data is pre-sorted longest first — take top 1000 visible
    features = sorted(features, key=lambda f: f['properties'].get('length', 0), reverse=True)[:1000]

    return jsonify({"type": "FeatureCollection", "features": features})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
