var CprMap = (function() {
  var OPM_GROUPS = [
    { label: '3ª CIPM', color: '#e53935', names: ['America Dourada','Bonito','Cafarnaum','Morro do Chapéu','Morro do Chapueu','Mulungu do Morro'] },
    { label: '10ª CIPM', color: '#1E88E5', names: ['Central','Gentio do Ouro','Ipupiara','Itaguacu da Bahia','Xique-Xique'] },
    { label: '7º BPM',  color: '#43A047', names: ['Barra do Mendes','Barro Alto','Canarana','Ibipeba','Ibitita','Irece','Joao Dourado','Jussara','Lapao','Presidente Dutra','Sao Gabriel','Uibai'] }
  ];

  var OCORRENCIA_COLORS = {
    "Homicídio":"#dc2626","Feminicídio":"#991b1b","Tentativa de Homicídio":"#ef4444",
    "Latrocínio":"#f97316","Incêndio Criminoso":"#ea580c","Extorsão":"#f59e0b",
    "Roubo":"#eab308","Roubo a Banco":"#ca8a04","Roubo de Veículo":"#a16207",
    "Furto":"#d97706","Furto de Veículo":"#92400e",
    "Estupro":"#a855f7","Estupro de Vulnerável":"#7c3aed","Sequestro":"#9333ea","Atentado ao Pudor":"#c084fc","Corrupção de Menores":"#d8b4fe",
    "Violência Doméstica - LMP":"#ec4899",
    "Lesão Corporal":"#3b82f6","Dano ao Patrimônio":"#2563eb","Ameaça":"#60a5fa","Direção Perigosa":"#06b6d4","Perturbação do Sossego":"#22d3ee","Receptação":"#0ea5e9","Estelionato":"#0284c7","Acidente de Trânsito":"#14b8a6","Atropelamento":"#0d9488","Violação de Domicílio":"#0891b2",
    "Tráfico de Drogas":"#22c55e","Porte de Drogas":"#16a34a","Porte Ilegal de Arma":"#65a30d",
    "Desaparecimento":"#94a3b8","Suicídio":"#6b7280","Achado de Cadáver":"#4b5563","Crime Cibernético":"#8b5cf6",
    "ACIDENTE":"#dc2626","ROUBO":"#eab308","ASSALTO":"#f97316","HOMICIDIO":"#dc2626","OUTRO":"#9ca3af",
    "Outros":"#9ca3af"
  };

  var OCORRENCIA_RADIUS = {
    "Homicídio":10,"Feminicídio":11,"Tentativa de Homicídio":9,"Latrocínio":10,
    "Estupro":9,"Estupro de Vulnerável":9,"Sequestro":8,"Incêndio Criminoso":8,
    "ACIDENTE":9,"HOMICIDIO":10,"ASSALTO":8,"ROUBO":8
  };

  var _geojsonCache = null;
  var _normalizeMap = {};

  function normalizeName(s) {
    return String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  }

  function escapeHtml(s) {
    if (s === null || s === undefined) return '';
    return String(s).replace(/[&<>"']/g, function(c) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':"&quot;","'":'&#39;'}[c];
    });
  }

  function buildLookups(municipios) {
    var ibgeToRow = {}, nameToRow = {}, nameToOpm = {};
    municipios.forEach(function(r) {
      if (r.codigo_ibge) ibgeToRow[String(r.codigo_ibge).trim()] = r;
      nameToRow[normalizeName(r.nome)] = r;
    });
    OPM_GROUPS.forEach(function(g) {
      g.names.forEach(function(n) { nameToOpm[normalizeName(n)] = g; });
    });
    return { ibgeToRow: ibgeToRow, nameToRow: nameToRow, nameToOpm: nameToOpm };
  }

  function findOpm(lookups, nome, ibge) {
    if (ibge && lookups.ibgeToRow[String(ibge).trim()]) {
      var dbMun = lookups.ibgeToRow[String(ibge).trim()];
      var key = normalizeName(dbMun.nome);
      if (lookups.nameToOpm[key]) return lookups.nameToOpm[key];
    }
    if (nome) return lookups.nameToOpm[normalizeName(nome)];
    return null;
  }

  function findRow(lookups, nome, ibge) {
    if (ibge && lookups.ibgeToRow[String(ibge).trim()]) return lookups.ibgeToRow[String(ibge).trim()];
    if (nome) return lookups.nameToRow[normalizeName(nome)];
    return null;
  }

  function extractIbge(f) {
    var p = (f && f.properties) || {};
    return String((f && (f.id || p.codarea || p.id || p.codigo_ibge || ''))).trim();
  }

  function getStyle(lookups, OPACITY) {
    return function(feature) {
      var props = feature && feature.properties || {};
      var g = findOpm(lookups, props.name, extractIbge(feature));
      if (g) return { color: g.color, weight: 1, fillColor: g.color, fillOpacity: OPACITY };
      return { color: '#ccc', weight: 0.5, fillColor: '#e0e0e0', fillOpacity: 0.15 };
    };
  }

  function init(config) {
    var el = document.getElementById(config.mapId);
    if (!el || typeof L === 'undefined') return null;

    var lookups = buildLookups(config.municipios || []);
    var municipios = config.municipios || [];
    var ocorrencias = config.ocorrencias || [];
    var OPACITY = 0.45;

    var map = L.map(config.mapId, { zoomControl: true, attributionControl: true });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18, attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

    var municLayer = L.layerGroup().addTo(map);
    var outlineLayer = L.layerGroup().addTo(map);
    var ocorrenciaLayer = L.layerGroup().addTo(map);
    var legendCtrl = null;
    var ocorrenciaLegendCtrl = null;

    function addLegend() {
      if (legendCtrl) { map.removeControl(legendCtrl); legendCtrl = null; }
      var div = L.control({ position: 'bottomright' });
      div.onAdd = function() {
        var el = L.DomUtil.create('div', '');
        el.style.cssText = 'background:#fff;padding:10px 14px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,.18);font:13px/1.6 Inter,system-ui,sans-serif;color:#222';
        var html = '<div style="font-weight:700;margin-bottom:5px;font-size:14px">OPM / CPR-CN</div>';
        OPM_GROUPS.forEach(function(g) {
          html += '<div style="display:flex;align-items:center;gap:7px;margin:2px 0"><span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:' + g.color + '"></span> ' + g.label + '</div>';
        });
        html += '<div style="display:flex;align-items:center;gap:7px;margin-top:5px;padding-top:5px;border-top:1px solid #ccc"><span style="display:inline-block;width:22px;height:0;border-top:3px dashed #000"></span> CPR-CN</div>';
        el.innerHTML = html;
        return el;
      };
      legendCtrl = div.addTo(map);
    }

    function addOcorrenciaLegend(tiposVisiveis) {
      if (ocorrenciaLegendCtrl) { map.removeControl(ocorrenciaLegendCtrl); ocorrenciaLegendCtrl = null; }
      if (!tiposVisiveis || !tiposVisiveis.length) return;
      var div = L.control({ position: 'bottomleft' });
      div.onAdd = function() {
        var el = L.DomUtil.create('div', '');
        el.style.cssText = 'background:#fff;padding:8px 12px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,.18);font:12px/1.5 Inter,system-ui,sans-serif;color:#222;max-height:200px;overflow-y:auto';
        var html = '<div style="font-weight:700;margin-bottom:4px;font-size:13px">🚨 Tipos Visíveis</div>';
        tiposVisiveis.forEach(function(t) {
          var c = OCORRENCIA_COLORS[t] || '#9ca3af';
          html += '<div style="display:flex;align-items:center;gap:6px;margin:1px 0"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:' + c + '"></span> ' + escapeHtml(t) + '</div>';
        });
        el.innerHTML = html;
        return el;
      };
      ocorrenciaLegendCtrl = div.addTo(map);
    }

    function addOcorrenciaMarkers(tipoFilter) {
      ocorrenciaLayer.clearLayers();
      var filtered = ocorrencias;
      if (tipoFilter) {
        filtered = ocorrencias.filter(function(o) { return o.tipo === tipoFilter; });
      }
      filtered.forEach(function(o) {
        if (!o.latitude || !o.longitude) return;
        var cor = OCORRENCIA_COLORS[o.tipo] || '#9ca3af';
        var raio = OCORRENCIA_RADIUS[o.tipo] || 7;
        L.circleMarker([o.latitude, o.longitude], {
          radius: raio, color: cor, fillColor: cor, fillOpacity: 0.7, weight: 2, opacity: 0.9
        }).bindPopup(
          '<b>' + escapeHtml(o.tipo) + '</b><br>' +
          (o.data_hora || '').replace('T', ' ') + '<br>' +
          escapeHtml(o.cidade || '') +
          (o.vtr ? '<br><b>VTR:</b> ' + escapeHtml(o.vtr) : '') +
          (o.descricao ? '<br><i>' + escapeHtml(o.descricao) + '</i>' : '')
        ).addTo(ocorrenciaLayer);
      });
      var tiposVisiveis = [];
      var seen = {};
      ocorrencias.forEach(function(o) {
        if (o.latitude && o.longitude && !seen[o.tipo]) {
          if (!tipoFilter || o.tipo === tipoFilter) {
            tiposVisiveis.push(o.tipo);
            seen[o.tipo] = true;
          }
        }
      });
      tiposVisiveis.sort();
      addOcorrenciaLegend(tiposVisiveis);
    }

    function fallbackMarkers() {
      municLayer.clearLayers();
      var latlngs = [];
      municipios.forEach(function(r) {
        if (!r.latitude || !r.longitude) return;
        var g = lookups.nameToOpm[normalizeName(r.nome)];
        var color = g ? g.color : '#888';
        var opmLabel = g ? g.label : 'Sem OPM';
        latlngs.push([r.latitude, r.longitude]);
        L.circleMarker([r.latitude, r.longitude], {
          radius: 8, color: color, fillColor: color, fillOpacity: 0.6, weight: 2
        }).bindPopup(
          '<b>Município:</b> ' + escapeHtml(r.nome) + '<br><b>OPM:</b> ' + opmLabel +
          '<br><b>População:</b> ' + (r.populacao != null ? r.populacao.toLocaleString('pt-BR') : '-') +
          '<br><b>Prefeito:</b> ' + escapeHtml(r.prefeito || '-') + (r.partido ? ' / ' + escapeHtml(r.partido) : '')
        ).addTo(municLayer);
      });
      if (latlngs.length) map.fitBounds(latlngs, { padding: [30, 30] });
      addLegend();
    }

    function renderGeojson(geojson) {
      municLayer.clearLayers();
      outlineLayer.clearLayers();
      var matchedFeatures = [];
      var fc = geojson;
      if (fc.type === 'Feature') fc = { type: 'FeatureCollection', features: [fc] };
      if (!fc.features || !fc.features.length) { fallbackMarkers(); return; }

      function onEachFeature(feature, layer) {
        var props = feature && feature.properties || {};
        var g = findOpm(lookups, props.name, extractIbge(feature));
        var row = findRow(lookups, props.name, extractIbge(feature));
        var nome = row ? row.nome : (props.name || '');
        var opmLabel = g ? g.label : 'Sem OPM';
        var pop = row && row.populacao != null ? row.populacao.toLocaleString('pt-BR') : '-';
        var prefeito = row && row.prefeito ? escapeHtml(row.prefeito) : '-';
        var partido = row && row.partido ? escapeHtml(row.partido) : '';
        layer.bindPopup(
          '<b>' + escapeHtml(nome) + '</b><br>' +
          '<b>OPM:</b> ' + opmLabel + '<br>' +
          '<b>População:</b> ' + pop + '<br>' +
          '<b>Prefeito:</b> ' + prefeito + (partido ? ' / ' + partido : '')
        );
        layer.on({
          mouseover: function(e) {
            var l = e.target;
            l.setStyle({ weight: 3, fillOpacity: Math.min(OPACITY + 0.3, 1) });
            l.bringToFront();
          },
          mouseout: function(e) {
            var l = e.target;
            if (g) l.setStyle({ color: g.color, weight: 1, fillColor: g.color, fillOpacity: OPACITY });
            else l.setStyle({ color: '#ccc', weight: 0.5, fillColor: '#e0e0e0', fillOpacity: 0.15 });
          }
        });
      }

      var layer = L.geoJSON(fc, {
        style: getStyle(lookups, OPACITY),
        onEachFeature: function(feature, l) {
          onEachFeature(feature, l);
          var g = findOpm(lookups, feature && feature.properties && feature.properties.name, extractIbge(feature));
          if (g) matchedFeatures.push(feature);
        }
      });
      municLayer.addLayer(layer);

      if (typeof turf !== 'undefined' && matchedFeatures.length > 1) {
        try {
          var merged = matchedFeatures.reduce(function(a, b) { return turf.union(a, b); });
          if (merged) {
            L.geoJSON(merged, {
              style: { color: '#000', weight: 3, dashArray: '10,8', fillOpacity: 0 },
              interactive: false
            }).addTo(outlineLayer);
          }
        } catch(e) { console.warn('[cpr-map] dissolve error:', e); }
      }

      if (matchedFeatures.length) {
        map.fitBounds(L.geoJSON({ type: 'FeatureCollection', features: matchedFeatures }).getBounds(), { padding: [30, 30] });
      }
      addLegend();
    }

    function tryFetchGeojson(idx) {
      var GEO_URLS = [
        'https://cdn.jsdelivr.net/gh/tbrugz/geodata-br@master/geojson/geojs-29-mun.json',
        'https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-29-mun.json'
      ];
      if (idx >= GEO_URLS.length) { fallbackMarkers(); return; }
      var timeoutMs = 15000;
      Promise.race([
        fetch(GEO_URLS[idx]).then(function(r) { return r.ok ? r.json() : Promise.reject(r.status); }),
        new Promise(function(_, rej) { setTimeout(function() { rej('timeout'); }, timeoutMs); })
      ]).then(function(data) {
        if (!data || !data.features || !data.features.length) throw 'Empty';
        _geojsonCache = data;
        renderGeojson(data);
      }).catch(function() { tryFetchGeojson(idx + 1); });
    }

    fallbackMarkers();
    addOcorrenciaMarkers();
    tryFetchGeojson(0);

    var toggleMunic = function() {
      var z = map.getZoom();
      if (z >= 13) {
        if (map.hasLayer(municLayer)) map.removeLayer(municLayer);
        if (map.hasLayer(outlineLayer)) map.removeLayer(outlineLayer);
      } else {
        if (!map.hasLayer(municLayer)) municLayer.addTo(map);
        if (!map.hasLayer(outlineLayer)) outlineLayer.addTo(map);
      }
    };
    map.on('zoomend', toggleMunic);
    setTimeout(toggleMunic, 300);

    return {
      map: map,
      addOcorrenciaMarkers: addOcorrenciaMarkers,
      getGeojsonCache: function() { return _geojsonCache; }
    };
  }

  return { init: init, OPM_GROUPS: OPM_GROUPS, OCORRENCIA_COLORS: OCORRENCIA_COLORS };
})();
