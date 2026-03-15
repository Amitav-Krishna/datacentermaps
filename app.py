from flask import Flask, jsonify, render_template_string
import json
import os

app = Flask(__name__)

BASE = os.path.dirname(__file__)
BOUNDARY_FILES = (
    "data/boundaries/can_scored.geojson",
    "data/boundaries/chn_scored.geojson",
    "data/boundaries/mex_scored.geojson",
)

_cache = {}

def load_geojson(path):
    if path not in _cache:
        with open(os.path.join(BASE, path)) as f:
            _cache[path] = json.load(f)
    return _cache[path]


def load_scored_boundaries():
    cache_key = "scored_boundaries_merged"
    if cache_key not in _cache:
        merged_features = []
        for path in BOUNDARY_FILES:
            geojson = load_geojson(path)
            merged_features.extend(geojson.get("features", []))
        _cache[cache_key] = {"type": "FeatureCollection", "features": merged_features}
    return _cache[cache_key]


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Data Center Heatmap</title>
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
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="loading" id="loading">Loading map data...</div>

    <div class="info-panel">
        <h1>Data Center Suitability</h1>
        <p>Heatmap of scored regions &mdash; hover for details</p>
    </div>

    <div class="legend">
        <h3>Suitability Score</h3>
        <div class="legend-item"><div class="legend-color" style="background:#1a9641"></div> Excellent (80-100)</div>
        <div class="legend-item"><div class="legend-color" style="background:#a6d96a"></div> Good (60-80)</div>
        <div class="legend-item"><div class="legend-color" style="background:#ffffbf"></div> Moderate (40-60)</div>
        <div class="legend-item"><div class="legend-color" style="background:#fdae61"></div> Below avg (20-40)</div>
        <div class="legend-item"><div class="legend-color" style="background:#d7191c"></div> Poor (0-20)</div>
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
            center: [30.0, -15.0],
            zoom: 2,
            zoomControl: false,
            minZoom: 2
        });

        L.control.zoom({ position: 'bottomright' }).addTo(map);

        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; OpenStreetMap &copy; CARTO',
            maxZoom: 19
        }).addTo(map);

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

        let activeLayer = null;

        function addRegionLayer(geojson) {
            return L.geoJSON(geojson, {
                style: function(feature) {
                    const score = feature.properties.score;
                    return {
                        fillColor: scoreToColor(score),
                        fillOpacity: scoreToOpacity(score),
                        color: '#fff',
                        weight: 0.5,
                        opacity: 0.5
                    };
                },
                onEachFeature: function(feature, layer) {
                    layer.on('mouseover', function(e) {
                        if (activeLayer) {
                            activeLayer.setStyle({ weight: 0.5, color: '#fff' });
                        }
                        this.setStyle({ weight: 2, color: '#333' });
                        this.bringToFront();
                        activeLayer = this;

                        const props = feature.properties;
                        hoverInfo.style.display = 'block';

                        hoverLoc.textContent = props.NAME || 'Unknown region';
                        if (props.COUNTRY && props.STATE) {
                            hoverCounty.textContent = props.STATE + ', ' + props.COUNTRY;
                        } else if (props.COUNTRY) {
                            hoverCounty.textContent = props.COUNTRY;
                        } else if (props.STATE) {
                            hoverCounty.textContent = props.STATE;
                        } else {
                            hoverCounty.textContent = '';
                        }

                        hoverScore.textContent = props.score + '/100';
                        hoverScore.style.color = scoreToColor(props.score);
                        hoverLabel.textContent = scoreToLabel(props.score);

                        let lines = [];
                        lines.push('Power: ' + (props.power_price != null ? props.power_price + ' ¢/kWh (industrial)' : 'data not found'));
                        lines.push('Median home: ' + (props.home_value != null ? '$' + props.home_value.toLocaleString() : 'data not found'));
                        lines.push('Permits/1k pop: ' + (props.permits_pc != null ? props.permits_pc : 'data not found'));
                        lines.push('Regulatory freedom: ' + (props.reg_freedom != null ? props.reg_freedom : 'data not found'));
                        var details = lines.length ? lines.join('<br>') : '';
                        hoverDetails.innerHTML = details;
                    });
                    layer.on('mouseout', function(e) {
                        this.setStyle({ weight: 0.5, color: '#fff' });
                        hoverInfo.style.display = 'none';
                        activeLayer = null;
                    });
                }
            }).addTo(map);
        }

        fetch('/api/counties')
            .then(r => r.json())
            .then(geojson => {
                const layer = addRegionLayer(geojson);
                if (layer.getBounds && layer.getBounds().isValid()) {
                    map.fitBounds(layer.getBounds(), { padding: [20, 20] });
                }
                loading.style.display = 'none';
            });

        // Hide layers while panning for performance
        var pane = map.getPane('overlayPane');
        map.on('movestart', function() {
            pane.style.visibility = 'hidden';
        });
        map.on('moveend', function() {
            pane.style.visibility = 'visible';
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
    return jsonify(load_scored_boundaries())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(debug=debug, host="0.0.0.0", port=port)
