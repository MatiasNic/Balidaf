/* Balidaf · interfaz (rediseño Claude Design). El motor de cálculo está en Python (balidaf/web/api.py). */
'use strict';

// =============================================================================================
// Utilidades
// =============================================================================================
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const miles = n => String(Math.abs(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
const fn = n => (n < 0 ? '-' : '') + miles(Math.round(n || 0));
function fmt(c) {
  if (c === null || c === undefined || c === '') return '';
  const neg = c < 0; c = Math.abs(Math.round(c));
  return (neg ? '-' : '') + miles(Math.floor(c / 100)) + ',' + String(c % 100).padStart(2, '0');
}
const dif = (o, n) => o === n ? esc(fmt(o))
  : `<span class="dif"><span class="a">${fmt(o)}</span><span class="f">→</span><span class="b">${fmt(n)}</span></span>`;
const chip = (txt, fam) => `<span class="chip c-${fam}">${esc(txt)}</span>`;
const debounce = (f, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => f(...a), ms); }; };

// ---- puente con Python: pywebview (ventana propia) o HTTP (modo navegador)
const MODO_WEB = new URLSearchParams(location.search).get('modo') === 'web';
async function api(metodo, ...args) {
  if (!MODO_WEB && window.pywebview && window.pywebview.api) return await window.pywebview.api[metodo](...args);
  const r = await fetch('/api/' + metodo, { method: 'POST', body: JSON.stringify(args) });
  return await r.json();
}
function listo() {
  return new Promise(res => {
    if (MODO_WEB || (window.pywebview && window.pywebview.api)) return res();
    window.addEventListener('pywebviewready', () => res(), { once: true });
  });
}

// =============================================================================================
// Estado
// =============================================================================================
const S = {
  ini: { codigos: {}, tipos: [], estados: [] }, est: { analizado: false }, tab: 'bal', tema: 'claro', ruta: '',
  ocupado: false, prog: null, version: -1, ultimoVisto: 0,
  grupos: [], gid: {},
  b: { estado: 'pend', tipo: 'Todos', q: '', sel: new Set(), foco: null, det: null },
  cruce: null, d: { estado: 'Todos', cod: 'Todos', q: '', sel: new Set(), foco: null },
  excel: null, x: { filtro: 'todas', q: '', vista: 'clave', cargadaVersion: -1, cargadaVista: '' },
};
const FAM_DEV = {
  'Corrección propuesta (sin aplicar)': 'pend', 'Corrección aplicada': 'ok', 'Requiere corrección manual': 'err',
  'Lo resuelve Sistemas / Presmed': 'warn', 'Ya cumple las reglas en el Excel': 'ok', 'No está en el Excel': 'neu'
};
const PROPUESTA = 'Corrección propuesta (sin aplicar)', APLICADA = 'Corrección aplicada';
const MANUAL = 'Requiere corrección manual', SISTEMAS = 'Lo resuelve Sistemas / Presmed';

// =============================================================================================
// Tabla virtual (sólo dibuja las filas visibles)
// =============================================================================================
class Tabla {
  constructor(cont, o) {
    this.o = Object.assign({ checks: false, alto: 33, vacio: 'Sin datos.' }, o);
    this.filas = []; this.vista = []; this.orden = [null, 0];
    this.el = document.createElement('div'); this.el.className = 'dt';
    this.in = document.createElement('div'); this.in.className = 'dt-in';
    this.el.appendChild(this.in); cont.appendChild(this.el);
    this.el.addEventListener('scroll', () => { if (!this._raf) this._raf = requestAnimationFrame(() => { this._raf = 0; this.pintar(); }); });
    this.el.addEventListener('click', e => this._clic(e));
    this.el.addEventListener('dblclick', e => { const r = e.target.closest('.dt-r'); if (r && !e.target.closest('.chk') && this.o.alDoble) this.o.alDoble(this._fila(r.dataset.k)); });
    new ResizeObserver(() => this.pintar()).observe(this.el);
  }
  get grid() { return (this.o.checks ? '36px ' : '') + this.o.cols.map(c => c.w || '120px').join(' '); }
  set(filas) { this.filas = filas || []; this._ordenar(); this.pintar(true); }
  _fila(k) { return this.vista.find(f => String(this.o.key(f)) === String(k)); }
  _ordenar() {
    const [col, d] = this.orden;
    this.vista = this.filas.slice();
    if (col !== null && d) {
      const c = this.o.cols[col], v = c.val || (r => r[c.k]);
      this.vista.sort((a, b) => { const x = v(a), y = v(b); return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y), 'es', { numeric: true })) * d; });
    }
  }
  _clic(e) {
    const h = e.target.closest('.dt-h');
    if (h) {
      if (e.target.closest('.chk')) { this._todos(); return; }
      const c = e.target.closest('[data-c]');
      if (c) { const i = +c.dataset.c; const [col, d] = this.orden; this.orden = col !== i ? [i, 1] : (d === 1 ? [i, -1] : [null, 0]); this._ordenar(); this.pintar(true); }
      return;
    }
    const r = e.target.closest('.dt-r'); if (!r) return;
    const f = this._fila(r.dataset.k); if (!f) return;
    if (e.target.closest('.chk') && this.o.sel) {
      const k = this.o.key(f); this.o.sel.has(k) ? this.o.sel.delete(k) : this.o.sel.add(k);
      this.pintar(true); if (this.o.alMarcar) this.o.alMarcar(); return;
    }
    if (this.o.alEnfocar) this.o.alEnfocar(f);
  }
  _todos() {
    const s = this.o.sel; const todos = this.vista.every(f => s.has(this.o.key(f)));
    this.vista.forEach(f => todos ? s.delete(this.o.key(f)) : s.add(this.o.key(f)));
    this.pintar(true); if (this.o.alMarcar) this.o.alMarcar();
  }
  marcarFoco(k) {
    this.in.querySelectorAll('.dt-r.foco').forEach(r => r.classList.remove('foco'));
    const r = this.in.querySelector(`.dt-r[data-k="${CSS.escape(String(k))}"]`); if (r) r.classList.add('foco');
  }
  pintar(forzar) {
    const o = this.o, alto = o.alto, n = this.vista.length;
    const top = this.el.scrollTop, vh = this.el.clientHeight || 600;
    const s0 = Math.max(0, Math.floor(top / alto) - 8), s1 = Math.min(n, Math.ceil((top + vh) / alto) + 8);
    if (!forzar && this._rango && this._rango[0] === s0 && this._rango[1] === s1) return;
    this._rango = [s0, s1];
    const sel = o.sel, foco = o.foco ? o.foco() : null;
    let marcadosVista = 0; if (o.checks) this.vista.forEach(f => { if (sel.has(o.key(f))) marcadosVista++; });
    const caja = on => `<div class="chk"><i class="${on === 2 ? 'on' : on === 1 ? 'mix' : ''}">${on === 2 ? '✓' : on === 1 ? '–' : ''}</i></div>`;
    const [col, d] = this.orden;
    let html = `<div class="dt-h" style="grid-template-columns:${this.grid}">` +
      (o.checks ? caja(n && marcadosVista === n ? 2 : marcadosVista ? 1 : 0) : '') +
      o.cols.map((c, i) => `<div data-c="${i}" class="ord ${c.al === 'r' ? 'der' : ''}" title="${esc(c.t)}">${esc(c.t)}${col === i && d ? `<span class="fl">${d === 1 ? '▲' : '▼'}</span>` : ''}</div>`).join('') + '</div>';
    html += `<div style="height:${s0 * alto}px"></div>`;
    for (let i = s0; i < s1; i++) {
      const f = this.vista[i], k = o.key(f), fam = o.fam ? o.fam(f) : '';
      html += `<div class="dt-r ${fam ? 'r-' + fam : ''} ${foco !== null && String(foco) === String(k) ? 'foco' : ''}" data-k="${esc(k)}" style="grid-template-columns:${this.grid}">` +
        (o.checks ? caja(sel.has(k) ? 2 : 0) : '') +
        o.cols.map(c => { const v = c.html ? c.html(f) : esc(c.fmt ? c.fmt(f[c.k], f) : f[c.k]); return `<div class="${c.al === 'r' ? 'der' : ''} ${c.mono ? 'mono' : ''}" title="${esc(c.tip ? c.tip(f) : (c.fmt ? c.fmt(f[c.k], f) : f[c.k]))}">${v}</div>`; }).join('') + '</div>';
    }
    html += `<div style="height:${(n - s1) * alto}px"></div>`;
    if (!n) html += `<div class="dt-vacio">${esc(o.vacio)}</div>`;
    this.in.innerHTML = html;
  }
}

// =============================================================================================
// Encabezado, progreso, pestañas y pie
// =============================================================================================
function pintarCab() {
  const e = S.est;
  $('#cab').innerHTML = `<div class="marca"><div class="b">B</div><div class="n">Balidaf</div></div><div class="sepv"></div>
    <div class="sub ellip">Balanceo de subsidios · Rendición Mecanismo Integración (SSSalud)</div><div class="grow"></div>
    ${e.analizado ? `<div class="chip-arch"><div class="cuadro"></div><div class="nom ellip">${esc(e.archivo)}</div><div class="meta">${fn(e.lineas)} líneas · ${e.columnas} columnas</div></div>` : ''}
    <button class="btn-tema" id="btn-tema" title="${S.tema === 'oscuro' ? 'Modo claro' : 'Modo oscuro'}">${S.tema === 'oscuro' ? '☀' : '☾'}</button>`;
  $('#btn-tema').onclick = cambiarTema;
}

function pintarProg() {
  const p = S.prog || { estado: 'idle', titulo: 'Listo. Elegí un Excel y presioná «Analizar»', detalle: 'Nada se modifica hasta que lo apliques.', pasos: [], actual: -1, pct: 0 };
  const ic = { idle: ['var(--neu-bg)', 'var(--ink3)', '●'], run: ['var(--accent-soft)', 'var(--accent)', '…'], done: ['var(--ok-bg)', 'var(--ok-fg)', '✓'], error: ['var(--err-bg)', 'var(--err-fg)', '!'] }[p.estado] || [];
  const barra = p.estado === 'error' ? 'var(--err-fg)' : p.estado === 'done' ? 'var(--ok-fg)' : 'var(--accent)';
  const pasos = (p.pasos || []).map((s, i) => {
    const hecho = i < p.actual || p.estado === 'done', act = i === p.actual && p.estado === 'run';
    return `<div class="paso" style="color:${act ? 'var(--accent)' : hecho ? 'var(--ink2)' : 'var(--ink3)'};font-weight:${act ? 600 : 400}"><span class="mk">${hecho ? '✓' : act ? '▸' : '○'}</span>${esc(s[1])}${i < p.pasos.length - 1 ? '<span class="sp">›</span>' : ''}</div>`;
  }).join('');
  $('#prog').innerHTML = `<div class="izq"><div class="ic" style="background:${ic[0]};color:${ic[1]}">${ic[2]}</div>
      <div style="min-width:0"><div class="tit ellip" style="${p.estado === 'error' ? 'color:var(--err-fg)' : ''}">${esc(p.titulo)}</div><div class="det ellip">${esc(p.detalle || '')}</div></div></div>
    <div class="pasos">${pasos}</div>
    <div class="pct num" style="color:${p.estado === 'idle' ? 'var(--ink3)' : barra}">${p.estado === 'idle' ? '' : Math.round(p.pct || 0) + ' %'}</div>
    <div class="barra ${p.indeterminado && p.estado === 'run' ? 'indet' : ''}"><div style="width:${p.pct || 0}%;background:${barra}"></div></div>`;
}

function pintarTabs() {
  const e = S.est, c = e.cruce;
  const tabs = [['bal', '1', 'Balancear', e.analizado && e.pend ? e.pend : 0], ['dev', '2', 'Devolución SSS', c ? (c.por_estado[PROPUESTA] || 0) : 0],
  null, ['exc', '', 'Ver Excel', 0], ['reg', '', 'Reglas de balanceo', 0]];
  $('#tabs').innerHTML = tabs.map(t => t ? `<button class="tab ${S.tab === t[0] ? 'act' : ''}" data-tab="${t[0]}">${t[1] ? `<span class="nro">${t[1]}</span>` : ''}<span>${t[2]}</span>${t[3] ? `<span class="badge">${fn(t[3])}</span>` : ''}</button>` : '<div class="sep"></div>').join('');
  $('#tabs').querySelectorAll('.tab').forEach(b => b.onclick = () => irA(b.dataset.tab));
}

function pintarPie() {
  const e = S.est, pie = $('#pie');
  pie.style.display = (S.tab === 'bal' || S.tab === 'dev') ? 'flex' : 'none';
  let tx = 'Primero analizá el Excel original (Paso 1).', circ = 'pend';
  if (e.analizado) {
    if (e.guardado && !e.cambios) { circ = 'hecho'; tx = `Guardado a las ${e.guardado.hora} como ${e.guardado.archivo}. Ya podés cargarlo en Presmed.`; }
    else { circ = e.apl ? 'actual' : 'pend'; tx = `${fn(e.apl)} correcciones aplicadas · se guarda como ${e.salida} (sin colores ni hojas nuevas). El original no se modifica.`; }
  }
  pie.innerHTML = `<span class="circ ${circ}">${circ === 'hecho' ? '✓' : '3'}</span><div class="t13">Guardar</div>
    <div class="tx ellip" title="${esc(tx)}">${esc(tx)}</div>
    <button class="btn" id="btn-informe" ${!e.analizado || S.ocupado ? 'disabled' : ''}>Exportar informe (opcional)…</button>
    <button class="btn ok" id="btn-guardar" ${!e.analizado || S.ocupado || (e.faltantes || []).length ? 'disabled' : ''}>Guardar Excel para Presmed</button>`;
  $('#btn-guardar').onclick = guardarExcel; $('#btn-informe').onclick = exportarInforme;
}

function irA(tab) {
  S.tab = tab;
  document.querySelectorAll('.pag').forEach(p => p.classList.remove('act'));
  $('#pag-' + tab).classList.add('act');
  pintarTabs(); pintarPie();
  if (tab === 'exc') cargarExcel();
}

function aviso(el, texto, tipo, accion) {
  const ic = { neutro: '○', info: 'i', ok: '✓', error: '!', warn: '!' }[tipo];
  el.className = 'aviso av-' + tipo;
  el.innerHTML = `<span class="ic">${ic}</span><div class="tx">${esc(texto)}</div>${accion ? `<button>${esc(accion[0])}</button>` : ''}`;
  if (accion) el.querySelector('button').onclick = accion[1];
}

function kpi(et, color, v, s, act) {
  return `<div class="kpi ${act ? 'act' : ''}"><div class="et"><span class="dot" style="background:${color}"></span><span class="ellip">${esc(et)}</span></div>
    <div style="display:flex;align-items:baseline;gap:8px;min-width:0"><div class="v" style="color:${color}">${v}</div><div class="s ellip">${esc(s || '')}</div></div></div>`;
}

// =============================================================================================
// 1 · Balancear
// =============================================================================================
let tablaB, tablaBD;
function armarBalancear() {
  $('#pag-bal').innerHTML = `
  <div class="card paso1"><span class="circ actual" id="b-c1">1</span><div class="t13">Excel original de Presmed</div>
    <div class="ruta vacia" id="b-ruta"></div>
    <button class="btn" id="b-exam">Examinar…</button><button class="btn prim" id="b-anal">Analizar</button></div>
  <div class="aviso" id="b-aviso"></div>
  <div class="kpis" id="b-kpis" style="grid-template-columns:repeat(4,minmax(0,1fr))"></div>
  <div class="card p2">
    <div class="p2cab"><span class="circ pend" id="b-c2">2</span><div class="t13">Revisá y aplicá las correcciones</div>
      <div class="muted ellip" style="font-size:12px">Nada cambia hasta que lo apliques. Podés deshacer hasta guardar.</div><div class="grow"></div>
      <div style="display:flex;align-items:center;gap:10px;flex:none"><div class="ink2 num" style="font-size:12px" id="b-corr"></div><div class="mini"><div id="b-mini" style="width:0"></div></div></div></div>
    <div id="b-cuerpo" style="display:none;flex:1;min-height:0;flex-direction:column">
      <div class="filtros"><div class="seg" id="b-seg"></div><select class="sel" id="b-tipo"></select>
        <div class="buscar"><span>⌕</span><input id="b-q" placeholder="Buscar CUIL o clave"><button id="b-qx" style="display:none">×</button></div>
        <div class="grow"></div>
        <button class="btn m" id="b-undo"></button><button class="btn m" id="b-sel"></button><button class="btn m prim" id="b-todas"></button></div>
      <div class="resumen"><span id="b-res"></span><span class="sel" id="b-selres"></span><button class="link" id="b-quitar" style="display:none">quitar selección</button>
        <div class="grow"></div><span class="muted">Clic en encabezado para ordenar · clic en fila para ver el detalle</span></div>
      <div class="zona-tabla" id="b-tabla"></div>
      <div class="detalle"><div class="dcab" id="b-dcab"></div><div class="dtabla" id="b-dtabla"></div></div>
    </div>
    <div class="vacio" id="b-vacio" style="border-top:1px solid var(--line)"></div>
  </div>`;
  $('#b-exam').onclick = examinar; $('#b-anal').onclick = analizarExcel;
  $('#b-tipo').onchange = e => { S.b.tipo = e.target.value; refrescarB(); };
  const q = $('#b-q'), qx = $('#b-qx');
  q.oninput = debounce(() => { S.b.q = q.value.trim(); qx.style.display = q.value ? '' : 'none'; refrescarB(); }, 220);
  qx.onclick = () => { q.value = ''; S.b.q = ''; qx.style.display = 'none'; refrescarB(); };
  $('#b-undo').onclick = () => deshacer(selB('apl'));
  $('#b-sel').onclick = () => aplicar(selB('pend'));
  $('#b-todas').onclick = () => aplicar(tablaB.vista.filter(g => g.estado === 'pend').map(g => g.id));
  $('#b-quitar').onclick = () => { S.b.sel.clear(); tablaB.pintar(true); marcadoB(); };
  tablaB = new Tabla($('#b-tabla'), {
    checks: true, sel: S.b.sel, key: g => g.id, fam: g => g.estado === 'pend' ? 'pend' : 'ok', foco: () => S.b.foco,
    vacio: 'No hay grupos con este filtro.',
    alEnfocar: g => { S.b.foco = g.id; tablaB.marcarFoco(g.id); cargarDetalleGrupo(g.id); },
    alDoble: g => verDetalleGrupo(g.id), alMarcar: marcadoB,
    cols: [
      { k: 'estado', t: 'Estado', w: '100px', html: g => g.estado === 'pend' ? chip('Pendiente', 'pend') : chip('Aplicada', 'ok') },
      { k: 'tipo', t: 'Tipo de corrección', w: '200px' }, { k: 'cuil', t: 'CUIL', w: '118px', mono: true },
      { k: 'cod', t: 'Práctica', w: '78px' }, { k: 'pres', t: 'Prestación', w: '92px' },
      { k: 'n', t: 'Líneas', w: '70px', al: 'r' }, { k: 'sub', t: 'Subsidio', w: '128px', al: 'r', fmt: fmt },
      { k: 'ao', t: 'Aplicado original', w: '140px', al: 'r', html: g => `<span class="ink2">${fmt(g.ao)}</span>` },
      { k: 'an', t: 'Aplicado corregido', w: '146px', al: 'r', html: g => `<b style="font-weight:600">${fmt(g.an)}</b>` },
      { k: 'dif', t: 'Diferencia', w: '120px', al: 'r', fmt: fmt },
      { k: 'errs', t: 'Errores SSS', w: 'minmax(110px,1fr)', mono: true }]
  });
  tablaBD = new Tabla($('#b-dtabla'), {
    key: l => l.fila, vacio: 'Sin grupo seleccionado.', foco: () => null, alDoble: l => abrirDetalle(l.fila),
    fam: l => l.retred ? 'vio' : '',
    cols: [{ k: 'fila', t: 'Fila', w: '64px', al: 'r' }, { k: 'clave', t: 'Clave', w: '130px', mono: true },
    { k: 'sol', t: 'Solicitado', w: '130px', al: 'r', fmt: fmt },
    { k: 'ret', t: 'Retenciones', w: '170px', al: 'r', html: l => dif(...l.ret), val: l => l.ret[1] },
    { k: 'apli', t: 'Aplicado (impor_apli_sss)', w: '230px', al: 'r', html: l => dif(...l.apli), val: l => l.apli[1] },
    { k: 'tr', t: 'Transferido (importe_transferido)', w: '240px', al: 'r', html: l => dif(...l.tr), val: l => l.tr[1] },
    { k: 'fdo', t: 'Fondos propios (fdo_ppio_ingre_cta_disca)', w: 'minmax(270px,1fr)', al: 'r', html: l => dif(...l.fdo), val: l => l.fdo[1] }]
  });
}
const selB = est => [...S.b.sel].filter(id => S.gid[id] && S.gid[id].estado === est);

function pintarBalancear() {
  const e = S.est, ruta = S.ruta || e.ruta || '';
  const r = $('#b-ruta'); r.textContent = ruta || 'Ningún archivo elegido · usá «Examinar…» para elegir el Excel original de Presmed';
  r.className = 'ruta' + (ruta ? '' : ' vacia'); r.title = ruta;
  $('#b-anal').textContent = e.analizado ? 'Volver a analizar' : 'Analizar';
  $('#b-anal').disabled = !ruta || S.ocupado; $('#b-exam').disabled = S.ocupado;
  $('#b-c1').className = 'circ ' + (e.analizado ? 'hecho' : 'actual'); $('#b-c1').textContent = e.analizado ? '✓' : '1';
  $('#b-c2').className = 'circ ' + (e.analizado ? 'actual' : 'pend');
  const av = $('#b-aviso'), K = $('#b-kpis');
  if (!e.analizado) {
    aviso(av, S.ocupado ? 'Analizando el Excel… esto puede tardar unos segundos.' : 'Todavía no se analizó ningún Excel. Elegí el archivo original de Presmed y presioná «Analizar».', 'neutro');
    K.innerHTML = kpi('Errores en el Excel (ahora)', 'var(--err-fg)', '–') + kpi('Correcciones pendientes', 'var(--pend-fg)', '–') + kpi('Correcciones aplicadas', 'var(--ok-fg)', '–') + kpi('Errores que NO se corrigen solos', 'var(--warn-fg)', '–');
    $('#b-cuerpo').style.display = 'none'; $('#b-vacio').style.display = 'flex'; $('#b-corr').textContent = ''; $('#b-mini').style.width = '0';
    $('#b-vacio').innerHTML = S.ocupado ? `<div class="skel"><div></div><div style="width:80%"></div><div style="width:90%"></div></div><div class="ink2">Calculando las correcciones… los botones se habilitan al terminar.</div>`
      : `<div class="t">Todavía no hay correcciones para revisar</div><div class="x">Elegí el Excel original de Presmed y presioná «Analizar». Balidaf revisa todas las reglas de la SSS, calcula la corrección de cada grupo y te la muestra acá sin aplicar nada.</div>`;
    return;
  }
  const verErr = e.manual ? [`Ver los ${fn(e.manual)} errores`, () => { S.x.filtro = 'err'; irA('exc'); }] : null;
  if ((e.faltantes || []).length) aviso(av, 'Al Excel le faltan columnas obligatorias: ' + e.faltantes.join(', '), 'error');
  else if (e.guardado && !e.cambios) aviso(av, `Excel guardado a las ${e.guardado.hora} como ${e.guardado.archivo}. Ya podés cargarlo en Presmed.`, 'ok');
  else if (e.pend && e.errores) aviso(av, `El Excel tiene ${fn(e.errores)} errores. Balidaf propone ${fn(e.pend)} correcciones: revisalas y aplicalas.${e.manual ? ` Además hay ${fn(e.manual)} errores para corregir a mano.` : ''}`, 'info', verErr);
  else if (e.pend) aviso(av, `Sin errores. Quedan ${fn(e.pend)} correcciones opcionales sin aplicar. Podés guardar el Excel (Paso 3).`, 'info');
  else if (e.errores) aviso(av, `Quedan ${fn(e.errores)} errores que el balanceo no puede corregir: hay que corregirlos en el Excel original y volver a analizar.`, 'error', verErr);
  else aviso(av, 'Sin errores. Guardá el Excel para Presmed (Paso 3).', 'ok');
  K.innerHTML = kpi('Errores en el Excel (ahora)', 'var(--err-fg)', fn(e.errores), `de ${fn(e.errores_antes)} en el original`) +
    kpi('Correcciones pendientes', 'var(--pend-fg)', fn(e.pend), `grupos · ${fn(e.pend_lineas)} líneas`, S.b.estado === 'pend') +
    kpi('Correcciones aplicadas', 'var(--ok-fg)', fn(e.apl), `grupos · ${fn(e.apl_lineas)} líneas`, S.b.estado === 'apl') +
    kpi('Errores que NO se corrigen solos', 'var(--warn-fg)', fn(e.manual), 'corregir a mano en el Excel');
  const ks = K.querySelectorAll('.kpi');
  ks[0].onclick = () => { S.x.filtro = 'err'; irA('exc'); }; ks[1].onclick = () => setEstadoB('pend');
  ks[2].onclick = () => setEstadoB('apl'); ks[3].onclick = () => { S.x.filtro = 'err'; irA('exc'); };
  const total = e.pend + e.apl;
  $('#b-corr').textContent = `${fn(e.apl)} de ${fn(total)} grupos corregidos`;
  $('#b-mini').style.width = (total ? 100 * e.apl / total : 100) + '%';
  $('#b-cuerpo').style.display = 'flex'; $('#b-vacio').style.display = 'none';
  refrescarB();
}
function setEstadoB(v) { S.b.estado = v; refrescarB(); pintarBalancear(); }

function refrescarB() {
  if (!S.est.analizado) return;
  const G = S.grupos, b = S.b, cnt = { pend: 0, apl: 0 };
  G.forEach(g => cnt[g.estado]++);
  $('#b-seg').innerHTML = [['pend', `Pendientes ${fn(cnt.pend)}`], ['apl', `Aplicadas ${fn(cnt.apl)}`], ['todas', `Todas ${fn(G.length)}`]]
    .map(([v, t]) => `<button class="${b.estado === v ? 'act' : ''}" data-v="${v}">${t}</button>`).join('');
  $('#b-seg').querySelectorAll('button').forEach(x => x.onclick = () => setEstadoB(x.dataset.v));
  const enEst = G.filter(g => b.estado === 'todas' || g.estado === b.estado);
  const porTipo = {}; enEst.forEach(g => porTipo[g.tipo] = (porTipo[g.tipo] || 0) + 1);
  $('#b-tipo').innerHTML = `<option value="Todos">Todos los tipos (${fn(enEst.length)})</option>` +
    S.ini.tipos.filter(t => porTipo[t] || t === b.tipo).map(t => `<option value="${esc(t)}">${esc(t)} (${fn(porTipo[t] || 0)})</option>`).join('');
  $('#b-tipo').value = b.tipo;
  const vis = enEst.filter(g => (b.tipo === 'Todos' || g.tipo === b.tipo) && (!b.q || g.cuil.includes(b.q) || g.claves.includes(b.q)));
  tablaB.set(vis);
  const lin = vis.reduce((a, g) => a + g.n, 0), d = vis.reduce((a, g) => a + g.dif, 0);
  $('#b-res').textContent = `${fn(vis.length)} grupos · ${fn(lin)} líneas · diferencia en aplicado: ${fmt(d)}`;
  marcadoB();
  if (b.foco !== null && S.gid[b.foco]) cargarDetalleGrupo(b.foco); else pintarDetalleGrupo(null);
}
function marcadoB() {
  const p = selB('pend').length, a = selB('apl').length, sel = [...S.b.sel].filter(id => S.gid[id]);
  const lista = tablaB.vista.filter(g => g.estado === 'pend').length, lib = !S.ocupado;
  $('#b-undo').textContent = `↶ Deshacer (${fn(a)})`; $('#b-undo').disabled = !a || !lib;
  $('#b-sel').textContent = `✓ Aplicar seleccionadas (${fn(p)})`; $('#b-sel').disabled = !p || !lib;
  $('#b-todas').textContent = `✓ Aplicar todas las de la lista (${fn(lista)})`; $('#b-todas').disabled = !lista || !lib;
  const lin = sel.reduce((x, id) => x + S.gid[id].n, 0);
  $('#b-selres').textContent = sel.length ? `Seleccionados: ${fn(sel.length)} grupos · ${fn(lin)} líneas` : '';
  $('#b-quitar').style.display = sel.length ? '' : 'none';
}
async function cargarDetalleGrupo(id) {
  const d = await api('detalle_grupo', id); S.b.det = d; pintarDetalleGrupo(d);
}
function pintarDetalleGrupo(d) {
  const c = $('#b-dcab');
  if (!d) { S.b.foco = null; c.innerHTML = `<div class="muted" style="font-size:12.5px">Seleccioná un grupo para ver el detalle línea por línea (original → corregido).</div>`; tablaBD.set([]); return; }
  const pend = d.estado === 'pend';
  c.innerHTML = `${chip(pend ? 'Pendiente' : 'Aplicada', pend ? 'pend' : 'ok')}<div class="t13">CUIL ${esc(d.cuil)} · práctica ${esc(d.cod)} · prestación ${esc(d.pres)}</div>
    <div class="ink2 ellip num" style="font-size:12.5px">Subsidio ${fmt(d.sub)} · aplicado ${fmt(d.ao)} → ${fmt(d.an)} · ${esc(d.tipo)}</div><div class="grow"></div>
    <span class="muted" style="font-size:12px;white-space:nowrap">Doble clic en una línea = detalle completo</span>
    <button class="btn s" id="b-gact" ${S.ocupado ? 'disabled' : ''}>${pend ? '✓ Aplicar este grupo' : '↶ Deshacer este grupo'}</button>`;
  $('#b-gact').onclick = () => pend ? aplicar([d.id]) : deshacer([d.id]);
  tablaBD.set(d.lineas);
}
function verDetalleGrupo(id) { const g = S.gid[id]; if (g) api('detalle_grupo', id).then(d => d.lineas.length && abrirDetalle(d.lineas[0].fila)); }

// =============================================================================================
// 2 · Devolución SSS
// =============================================================================================
let tablaD;
function armarDevolucion() {
  $('#pag-dev').innerHTML = `
  <div class="card guia" id="d-guia"></div>
  <div class="aviso" id="d-aviso"></div>
  <div class="kpis" id="d-kpis" style="grid-template-columns:repeat(5,minmax(0,1fr))"></div>
  <div class="card p2" id="d-card">
    <div id="d-cuerpo" style="display:none;flex:1;min-height:0;flex-direction:column">
      <div class="filtros" style="border-top:none"><select class="sel" id="d-est"></select><select class="sel" id="d-cod"></select>
        <div class="buscar"><span>⌕</span><input id="d-q" placeholder="Buscar CUIL o clave"><button id="d-qx" style="display:none">×</button></div>
        <div class="grow"></div>
        <button class="btn m" id="d-undo"></button><button class="btn m" id="d-sel"></button><button class="btn m prim" id="d-todas"></button></div>
      <div class="resumen"><span id="d-res"></span><span class="sel" id="d-selres"></span><div class="grow"></div><span class="muted">Clic = explicación abajo · doble clic = detalle de la línea</span></div>
      <div class="zona-tabla" id="d-tabla"></div>
      <div class="dexpl"><div class="dcab" id="d-dcab"></div><div class="grid" id="d-grid"></div></div>
    </div>
    <div class="vacio" id="d-vacio"></div>
  </div>`;
  $('#d-est').onchange = e => { S.d.estado = e.target.value; refrescarD(); pintarKpisD(); };
  $('#d-cod').onchange = e => { S.d.cod = e.target.value; refrescarD(); };
  const q = $('#d-q'), qx = $('#d-qx');
  q.oninput = debounce(() => { S.d.q = q.value.trim(); qx.style.display = q.value ? '' : 'none'; refrescarD(); }, 220);
  qx.onclick = () => { q.value = ''; S.d.q = ''; qx.style.display = 'none'; refrescarD(); };
  $('#d-undo').onclick = () => deshacer(gruposD([...S.d.sel], 'apl'));
  $('#d-sel').onclick = () => aplicar(gruposD([...S.d.sel], 'pend'));
  $('#d-todas').onclick = () => aplicar(gruposD(tablaD.vista.filter(l => l.estado === PROPUESTA).map(l => l.id), 'pend'));
  tablaD = new Tabla($('#d-tabla'), {
    checks: true, sel: S.d.sel, key: l => l.id, fam: l => FAM_DEV[l.estado] === 'neu' ? '' : FAM_DEV[l.estado], foco: () => S.d.foco,
    vacio: 'No hay líneas con este filtro.', alMarcar: marcadoD,
    alEnfocar: l => { S.d.foco = l.id; tablaD.marcarFoco(l.id); pintarExplicacion(l); },
    alDoble: l => l.fila && abrirDetalle(l.fila),
    cols: [{ k: 'clave', t: 'Clave', w: '120px', mono: true }, { k: 'cuil', t: 'CUIL', w: '118px', mono: true },
    { k: 'fila', t: 'Fila', w: '64px', al: 'r' }, { k: 'errs', t: 'Error SSS', w: '96px', mono: true, fmt: v => v.join('  '), val: l => l.errs.join(' ') },
    { k: 'estado', t: 'Estado', w: '250px', html: l => chip(l.estado, FAM_DEV[l.estado]) },
    { k: 'corr', t: 'Corrección propuesta (original → corregido)', w: 'minmax(480px,1fr)', fmt: v => v || '—' },
    { k: 'pend', t: 'Qué falta', w: '110px', html: l => `<span style="color:var(--err-fg)">${esc(l.pend.join(' '))}</span>`, val: l => l.pend.join(' ') }]
  });
}
function gruposD(ids, est) {
  const out = new Set(); ids.forEach(i => { const l = S.cruce.filas[i]; if (l && l.gid !== null && l.gest === est) out.add(l.gid); }); return [...out];
}
function pintarDevolucion() {
  const e = S.est, c = S.cruce, ok = !!e.analizado, err = !!e.txt_err;
  const pasos = [[ok ? 'hecho' : 'actual', 'Analizá el Excel original'], [err ? 'hecho' : ok ? 'actual' : 'pend', 'Cargá el TXT de errores de la SSS'], [c ? 'actual' : 'pend', 'Revisá y decidí qué corregir']];
  $('#d-guia').innerHTML = pasos.map(([s, t], i) => `${i ? '<span class="muted">›</span>' : ''}<div class="g ${s === 'actual' ? 'act' : ''}"><span class="circ ${s}">${s === 'hecho' ? '✓' : i + 1}</span>${t}</div>`).join('') +
    `<div class="grow"></div><div class="mono ink2 ellip" style="font-size:12px;max-width:260px" title="${esc((e.txt || []).join(' · '))}">${esc((e.txt || []).join(' · '))}</div>
    <button class="btn" id="d-ok" ${S.ocupado ? 'disabled' : ''}>Cargar TXT aceptados (_OK)…</button>
    <button class="btn prim" id="d-err" ${S.ocupado ? 'disabled' : ''}>${err ? 'Cargar otro TXT (_ERR)…' : 'Cargar TXT de errores (_ERR)…'}</button>`;
  $('#d-ok').onclick = () => cargarTxt('OK'); $('#d-err').onclick = () => cargarTxt('ERR');
  const av = $('#d-aviso');
  if (!c) {
    $('#d-kpis').innerHTML = kpi('Líneas rechazadas', 'var(--accent)', '–') + kpi('Con corrección propuesta', 'var(--pend-fg)', '–') + kpi('Corrección aplicada', 'var(--ok-fg)', '–') + kpi('Requieren corrección manual', 'var(--err-fg)', '–') + kpi('Las resuelve Sistemas', 'var(--warn-fg)', '–');
    $('#d-cuerpo').style.display = 'none'; $('#d-vacio').style.display = 'flex';
    if (!ok) {
      aviso(av, 'Primero analizá el Excel original en «1 · Balancear». Después cargá el TXT de errores que devolvió la SSS.', 'neutro');
      $('#d-vacio').innerHTML = `<div class="t">Falta analizar el Excel original</div><div class="x">Para cruzar los rechazos de la SSS, primero analizá el mismo Excel que se envió.</div><button class="btn" id="d-ir">Ir a «1 · Balancear»</button>`;
      $('#d-ir').onclick = () => irA('bal');
    } else {
      aviso(av, 'Cargá el TXT de errores (_ERR) que devolvió la SSS: Balidaf muestra qué rechazó y qué corrección propone. Nada se corrige hasta que vos lo apliques.', 'neutro');
      $('#d-vacio').innerHTML = `<div class="t">Esperando el TXT de errores de la SSS</div><div class="x">Archivo ######-AAAAMM_DR.DEVOLUCION_ERR.txt. Opcionalmente, también el _OK para saber cuántas líneas aceptadas cambian.</div>`;
    }
    return;
  }
  const n = c.por_estado, prop = n[PROPUESTA] || 0, man = n[MANUAL] || 0;
  if (prop) aviso(av, `${fn(prop)} líneas rechazadas tienen una corrección propuesta. Revisala y presioná «Corregir…» para aplicarla.${c.aceptadas ? ` Ojo: ${fn(c.aceptadas)} líneas ACEPTADAS por la SSS están en esos grupos y también cambian.` : ''}`, 'info');
  else if (man) aviso(av, `${fn(man)} líneas requieren corrección manual en el Excel original (ver «Qué falta»).`, 'error', [`Ver las ${fn(man)}`, () => { S.d.estado = MANUAL; refrescarD(); pintarKpisD(); }]);
  else aviso(av, 'No quedan correcciones pendientes para las líneas rechazadas. Guardá el Excel para Presmed (Paso 3).', 'ok');
  $('#d-cuerpo').style.display = 'flex'; $('#d-vacio').style.display = 'none';
  pintarKpisD(); refrescarD();
}
function pintarKpisD() {
  const c = S.cruce; if (!c) return; const n = c.por_estado, f = S.d.estado;
  const ks = [['Todos', 'Líneas rechazadas', 'var(--accent)', c.total], [PROPUESTA, 'Con corrección propuesta', 'var(--pend-fg)', n[PROPUESTA] || 0],
  [APLICADA, 'Corrección aplicada', 'var(--ok-fg)', n[APLICADA] || 0], [MANUAL, 'Requieren corrección manual', 'var(--err-fg)', n[MANUAL] || 0], [SISTEMAS, 'Las resuelve Sistemas', 'var(--warn-fg)', n[SISTEMAS] || 0]];
  $('#d-kpis').innerHTML = ks.map(k => kpi(k[1], k[2], fn(k[3]), '', f === k[0])).join('');
  $('#d-kpis').querySelectorAll('.kpi').forEach((el, i) => el.onclick = () => { S.d.estado = ks[i][0]; refrescarD(); pintarKpisD(); });
}
function refrescarD() {
  const c = S.cruce; if (!c) return; const d = S.d, F = c.filas;
  $('#d-est').innerHTML = `<option value="Todos">Todos los estados (${fn(F.length)})</option>` + S.ini.estados.filter(e => c.por_estado[e]).map(e => `<option value="${esc(e)}">${esc(e)} (${fn(c.por_estado[e])})</option>`).join('');
  $('#d-est').value = d.estado;
  const enEst = F.filter(l => d.estado === 'Todos' || l.estado === d.estado), cods = {};
  enEst.forEach(l => l.errs.forEach(x => cods[x] = (cods[x] || 0) + 1));
  $('#d-cod').innerHTML = `<option value="Todos">Todos los errores (${fn(enEst.length)})</option>` + Object.keys(cods).sort().map(x => `<option value="${x}">Error ${x} (${fn(cods[x])})</option>`).join('');
  $('#d-cod').value = cods[d.cod] ? d.cod : 'Todos'; if (!cods[d.cod]) d.cod = 'Todos';
  const vis = enEst.filter(l => (d.cod === 'Todos' || l.errs.includes(d.cod)) && (!d.q || l.cuil.includes(d.q) || l.clave.includes(d.q)));
  tablaD.set(vis);
  $('#d-res').textContent = `${fn(vis.length)} líneas · ${fn(vis.filter(l => l.estado === PROPUESTA).length)} con corrección propuesta`;
  marcadoD();
  const foco = d.foco !== null ? F[d.foco] : null; pintarExplicacion(foco);
}
function marcadoD() {
  const sel = [...S.d.sel].map(i => S.cruce && S.cruce.filas[i]).filter(Boolean), lib = !S.ocupado;
  const p = sel.filter(l => l.estado === PROPUESTA).length, a = sel.filter(l => l.estado === APLICADA).length;
  const lista = tablaD.vista.filter(l => l.estado === PROPUESTA).length;
  $('#d-undo').textContent = `↶ Deshacer (${fn(a)})`; $('#d-undo').disabled = !a || !lib;
  $('#d-sel').textContent = `✓ Corregir seleccionadas en el Excel (${fn(p)})`; $('#d-sel').disabled = !p || !lib;
  $('#d-todas').textContent = `✓ Corregir todas las de la lista (${fn(lista)})`; $('#d-todas').disabled = !lista || !lib;
  $('#d-selres').textContent = sel.length ? `Seleccionadas: ${fn(sel.length)} líneas` : '';
}
function pintarExplicacion(l) {
  const c = $('#d-dcab'), g = $('#d-grid');
  if (!l) { S.d.foco = null; c.innerHTML = `<div class="muted" style="font-size:12.5px">Seleccioná una línea para ver la explicación completa del error y de la corrección.</div>`; g.innerHTML = ''; return; }
  const fam = FAM_DEV[l.estado];
  c.innerHTML = `${chip(l.estado, fam)}<div class="t13">Clave ${esc(l.clave)} · CUIL ${esc(l.cuil)} · fila ${l.fila || '—'}</div><div class="grow"></div>
    ${l.fila ? '<button class="btn s" id="d-ver">Ver detalle de la línea</button>' : ''}
    ${l.estado === PROPUESTA ? `<button class="btn s prim" id="d-lact" ${S.ocupado ? 'disabled' : ''}>✓ Corregir esta línea</button>` : l.estado === APLICADA ? `<button class="btn s" id="d-lact" ${S.ocupado ? 'disabled' : ''}>↶ Deshacer</button>` : ''}`;
  if ($('#d-ver')) $('#d-ver').onclick = () => abrirDetalle(l.fila);
  if ($('#d-lact')) $('#d-lact').onclick = () => l.estado === PROPUESTA ? aplicar([l.gid]) : deshacer([l.gid]);
  const C = S.ini.codigos; let h = '';
  l.errs.forEach(x => { const d = C[x]; h += `<div class="et" style="color:var(--err-fg)">Error ${x}</div><div>${d ? `${esc(d.descripcion)} <span class="muted">→ ${esc(d.accion)} (lo resuelve: ${esc(d.resuelve)})</span>` : 'No figura en el instructivo'}</div>`; });
  if (l.corr) h += `<div class="et" style="color:var(--accent)">${l.estado === APLICADA ? 'Corrección aplicada' : 'Corrección propuesta'}</div><div class="num">${esc(l.corr)}</div>`;
  if (l.pend.length) h += `<div class="et" style="color:var(--err-fg)">Qué falta</div><div style="color:var(--err-fg)">${l.pend.map(x => `${x}: ${esc((C[x] || {}).descripcion || '')}`).join(' · ')}</div>`;
  const quien = { [SISTEMAS]: 'Sistemas / Presmed (formato del archivo o del envío).', [MANUAL]: 'A mano: corregir el dato en el Excel original y volver a analizar.', 'No está en el Excel': 'La clave no está en el Excel analizado: verificar que sea el mismo archivo enviado.' }[l.estado];
  if (quien) h += `<div class="et ink2">Quién lo resuelve</div><div>${quien}</div>`;
  g.innerHTML = h;
}

// =============================================================================================
// Ver Excel
// =============================================================================================
let tablaX;
const FILTROS_X = [['todas', 'Todas', null], ['pend', 'Corrección pendiente', 'pend'], ['ok', 'Corregidas', 'ok'], ['vio', 'Retenciones reducidas', 'vio'], ['err', 'Errores a corregir a mano', 'err'], ['warn', 'Advertencias', 'warn']];
const ESTADO_X = { err: ['Error a corregir a mano', 'err'], pend: ['Corrección pendiente', 'pend'], vio: ['Retenciones reducidas', 'vio'], ok: ['Corregida', 'ok'], warn: ['Advertencia', 'warn'], '': ['OK', ''] };
function armarExcel() {
  $('#pag-exc').innerHTML = `<div class="card p2">
    <div class="filtros" style="border-top:none;gap:8px"><span class="ink2" style="font-weight:600;font-size:12.5px;margin-right:4px">Mostrar</span><div id="x-chips" style="display:flex;gap:6px;flex-wrap:wrap"></div>
      <div class="grow"></div><div class="buscar"><span>⌕</span><input id="x-q" placeholder="Buscar CUIL o clave"><button id="x-qx" style="display:none">×</button></div></div>
    <div class="filtros" style="padding-top:0;border-top:none"><div class="seg" id="x-seg"></div></div>
    <div class="resumen"><b id="x-n" style="font-weight:600;color:var(--ink)"></b><span>Valores actuales (lo que se va a guardar). Las filas corregidas se ven en verde.</span><div class="grow"></div><span class="muted">Colores sólo en pantalla: el Excel se guarda sin formato · doble clic = detalle</span></div>
    <div class="zona-tabla" id="x-tabla"></div></div>`;
  const q = $('#x-q'), qx = $('#x-qx');
  q.oninput = debounce(() => { S.x.q = q.value.trim(); qx.style.display = q.value ? '' : 'none'; refrescarX(); }, 250);
  qx.onclick = () => { q.value = ''; S.x.q = ''; qx.style.display = 'none'; refrescarX(); };
}
async function cargarExcel() {
  const e = S.est;
  if (!e.analizado) { $('#x-tabla').innerHTML = `<div class="vacio"><div class="t">Todavía no hay datos</div><div class="x">Analizá el Excel original en «1 · Balancear» para verlo acá.</div></div>`; tablaX = null; pintarChipsX({}); return; }
  if (S.excel && S.x.cargadaVersion === S.version && S.x.cargadaVista === S.x.vista) { refrescarX(); return; }
  $('#x-n').textContent = 'Cargando…';
  S.excel = await api('excel', S.x.vista); S.x.cargadaVersion = S.version; S.x.cargadaVista = S.x.vista;
  const cols = [{ k: 'fila', t: 'Fila', w: '64px', al: 'r' }, { k: 'fam', t: 'Estado', w: '200px', html: r => ESTADO_X[r.fam][1] ? chip(ESTADO_X[r.fam][0], ESTADO_X[r.fam][1]) : '<span class="muted">OK</span>', val: r => ESTADO_X[r.fam][0] }]
    .concat(S.excel.cols.map((c, i) => ({ k: 'v' + i, t: c.t, al: c.m ? 'r' : '', w: c.m ? '150px' : (/clave|cuil|cuit|cbu/i.test(c.t) ? (c.t === 'cbu' ? '210px' : '120px') : '120px'), mono: /clave|cuil|cuit|cbu/i.test(c.t), fmt: c.m ? (v, r) => fmt(r.v[i]) : (v, r) => r.v[i], val: r => r.v[i] })));
  $('#x-tabla').innerHTML = '';
  tablaX = new Tabla($('#x-tabla'), { key: r => r.fila, fam: r => r.fam, foco: () => S.x.foco, cols, alEnfocar: r => { S.x.foco = r.fila; tablaX.marcarFoco(r.fila); }, alDoble: r => abrirDetalle(r.fila), vacio: 'No hay líneas con este filtro.' });
  refrescarX();
}
function pintarChipsX(cnt) {
  $('#x-chips').innerHTML = FILTROS_X.map(([v, t, f]) => `<button class="chipf ${S.x.filtro === v ? 'act' : ''}" data-v="${v}"><span class="q" style="${f ? `background:var(--${f}-bg);border-color:var(--${f}-fg)` : ''}"></span>${t}<span class="n">${cnt[v] !== undefined ? fn(cnt[v]) : ''}</span></button>`).join('');
  $('#x-chips').querySelectorAll('.chipf').forEach(b => b.onclick = () => { S.x.filtro = b.dataset.v; refrescarX(); });
  const ncol = S.est.columnas || 39;
  $('#x-seg').innerHTML = [['clave', 'Importes y datos clave'], ['todas', `Todas las columnas (${ncol})`]].map(([v, t]) => `<button class="${S.x.vista === v ? 'act' : ''}" data-v="${v}">${t}</button>`).join('');
  $('#x-seg').querySelectorAll('button').forEach(b => b.onclick = () => { S.x.vista = b.dataset.v; cargarExcel(); });
}
function refrescarX() {
  if (!S.excel || !tablaX) return;
  const F = S.excel.filas, cnt = { todas: F.length, pend: 0, ok: 0, vio: 0, err: 0, warn: 0 };
  F.forEach(r => { if (r.fam) cnt[r.fam]++; });
  pintarChipsX(cnt);
  const q = S.x.q, f = S.x.filtro;
  const vis = F.filter(r => (f === 'todas' || r.fam === f) && (!q || r.cuil.includes(q) || r.clave.includes(q)));
  tablaX.set(vis);
  $('#x-n').textContent = `${fn(vis.length)} de ${fn(F.length)} líneas`;
}

// =============================================================================================
// Reglas de balanceo (página de lectura)
// =============================================================================================
const LEE = ['clave_rendicion', 'cuil', 'cod_prestac', 'periodo_presentacion', 'perio_prestac', 'importe_subsidiado', 'importe_solicitado', 'retencion_ganancias', 'retencion_IIBB', 'otras_retnciones', 'fdo_ppio_otras_ctas', 'reversion_import_trasl', 'import_devuelto_cta_sss', 'saldo_no_apli', 'recup_fdos_ppios'];
const DESC_TIPOS = { 'Aplicado mayor al subsidio': 'Se había aplicado más que el subsidio del grupo.', 'Aplicado menor al subsidio': 'Se había aplicado menos que el subsidio.', 'Fondos propios / reparto': 'El total estaba bien pero faltaban fondos propios o el reparto entre líneas.', 'Ajuste de centavos': 'Ningún importe cambia más de $1.', 'Reduce retenciones': 'El subsidio no alcanza para cubrir las retenciones de alguna línea.', 'No se puede balancear': 'El subsidio es mayor a lo que se puede aplicar: revisión manual.' };
let filtroCtrl = 'Todos';
function armarReglas() {
  const cm = (l, c) => l.map(x => `<span class="cm ${c}">${x}</span>`).join('');
  $('#pag-reg').innerHTML = `<div class="lectura" id="lectura"><div class="in">
   <h1>Cómo balancea Balidaf</h1>
   <p>Balidaf trabaja sobre la primera hoja del Excel de Presmed. Primero propone la corrección y sólo la aplica cuando vos lo decidís (botones «Aplicar…» / «Corregir…»).</p>
   <div class="indice">${[['r-col', 'Columnas'], ['r-calc', 'Cálculo'], ['r-tipos', 'Tipos'], ['r-reglas', 'Reglas 622–624'], ['r-ej', 'Ejemplo'], ['r-ctrl', 'Controles SSS']].map(([i, t]) => `<button data-i="${i}">${t}</button>`).join('')}</div>
   <div class="flujo">${[['Paso 1', 'Analizar', 'Lee el Excel, revisa las reglas de la SSS en el original, calcula la corrección de cada grupo y valida cómo quedaría.'], ['Paso 2', 'Revisar y aplicar', 'Filtrás, ordenás, mirás el detalle original → corregido y aplicás todas, algunas o las de un tipo. Se puede deshacer.'], ['Paso 3', 'Guardar para Presmed', 'Genera &lt;archivo&gt;_balidaf.xlsx. Sólo cambian valores: sin colores, formatos, fórmulas ni hojas nuevas.'], ['Si la SSS rechaza', 'Devolución SSS', 'Se cargan los TXT _ERR (y _OK), se cruzan por clave_rendicion y decidís qué corregir.']].map(([k, t, x]) => `<div class="card"><div class="k">${k}</div><div class="t">${t}</div><div class="x">${x}</div></div>`).join('')}</div>
   <div class="card sec" id="r-col"><h2>1 · Columnas</h2><div class="cols">
     <div class="et">Lee</div><div>${cm(LEE, 'neu')}</div>
     <div class="et">Puede modificar</div><div>${cm(['impor_apli_sss', 'importe_transferido', 'fdo_ppio_ingre_cta_disca'], 'pend')}<br>${cm(['retencion_ganancias', 'retencion_IIBB', 'otras_retnciones'], 'vio')}<span class="muted" style="font-size:12px">sólo si el subsidio no alcanza a cubrirlas</span></div>
     <div class="et">Nunca modifica</div><div class="ink2" style="line-height:1.5">Campos 2 a 9 de la SSS (rnos, tipo_archi, periodo_presentacion, perio_prestac, cuil, cod_prestac, importe_subsidiado, importe_solicitado), CUIT, CBU, órdenes de pago, fechas, cheque, recibo y observaciones.</div></div></div>
   <div class="card sec" id="r-calc"><h2>2 · Grupos y cálculo</h2><p style="margin-bottom:10px">Las líneas se agrupan como lo controla la SSS en la regla 624. El subsidio se informa en una línea del grupo y se reparte entre todas sus líneas. Si el grupo ya cumple 622, 623 y 624, no se toca. Todo se calcula en centavos exactos.</p>
<pre class="code">GRUPO       = cuil + periodo_presentacion + perio_prestac + cod_prestac      (regla 624)

SUBSIDIO    = Σ importe_subsidiado del grupo
A_APLICAR   = SUBSIDIO − Σ (reversion_import_trasl + import_devuelto_cta_sss + saldo_no_apli + recup_fdos_ppios)

Por línea:
  OTROS        = fdo_ppio_otras_ctas + reversion_import_trasl + import_devuelto_cta_sss + saldo_no_apli + recup_fdos_ppios
  TOPE         = importe_solicitado − OTROS
  RETENCIONES  = retencion_ganancias + retencion_IIBB + otras_retnciones

Orden de reparto: primero las líneas CON retenciones (el transferido nunca queda negativo), luego el resto.

  impor_apli_sss            = mínimo entre TOPE y lo que queda de A_APLICAR
  si RETENCIONES &gt; impor_apli_sss → se reducen ganancias → IIBB → otras (transferido = 0)
  importe_transferido       = impor_apli_sss − RETENCIONES
  fdo_ppio_ingre_cta_disca  = importe_solicitado − impor_apli_sss − OTROS</pre></div>
   <div class="card sec" id="r-tipos"><h2>3 · Tipos de corrección</h2><div class="marco"><table class="tabla-s"><tr><th style="width:260px">Tipo</th><th>Cuándo</th></tr>${S.ini.tipos.map(t => `<tr><td style="font-weight:500">${esc(t)}</td><td class="ink2">${esc(DESC_TIPOS[t] || '')}</td></tr>`).join('')}</table></div></div>
   <div class="card sec" id="r-reglas"><h2>4 · Reglas que debe cumplir el resultado</h2><div class="regla">
     <div class="c">622</div><div class="f">impor_apli_sss = importe_transferido + retencion_ganancias + retencion_IIBB + otras_retnciones</div>
     <div class="c">623</div><div class="f">importe_solicitado = fdo_ppio_ingre_cta_disca + fdo_ppio_otras_ctas + impor_apli_sss + reversion_import_trasl + import_devuelto_cta_sss + saldo_no_apli + recup_fdos_ppios <span class="muted">(no aplica a tipo DB)</span></div>
     <div class="c">624</div><div class="f">Por GRUPO: Σ importe_subsidiado = Σ (impor_apli_sss + reversion_import_trasl + import_devuelto_cta_sss + saldo_no_apli + recup_fdos_ppios)</div></div></div>
   <div class="card sec" id="r-ej"><h2>5 · Ejemplo (caso real de la rendición 202606)</h2><p style="margin-bottom:10px">Subsidio 1.010.735,49 · solicitado 1.364.492,91 · retenciones 27.289,86 + 27.289,86</p>
     <div class="marco"><table class="tabla-s num"><tr><th></th><th class="der">Aplicado</th><th class="der">Transferido</th><th class="der">Fondos propios</th><th>Resultado</th></tr>
     <tr><td style="font-weight:500">Original</td><td class="der">1.364.492,91</td><td class="der">1.309.913,19</td><td class="der">0,00</td><td>${chip('Error 624', 'err')}</td></tr>
     <tr><td style="font-weight:500">Corregido</td><td class="der"><b>1.010.735,49</b></td><td class="der"><b>956.155,77</b></td><td class="der"><b>353.757,42</b></td><td>${chip('OK', 'ok')}</td></tr></table></div></div>
   <div class="card sec" id="r-ctrl"><h2>6 · Todos los controles (instructivo SSS, Anexos III y IV)</h2><div class="seg" id="r-seg" style="display:inline-flex;margin-bottom:10px"></div><div class="marco" id="r-tabla"></div></div>
  </div></div>`;
  $('#pag-reg').querySelectorAll('.indice button').forEach(b => b.onclick = () => $('#' + b.dataset.i).scrollIntoView({ behavior: 'smooth', block: 'start' }));
  pintarControles();
}
function pintarControles() {
  const fam = { Balanceo: 'pend', Manual: 'err', Sistemas: 'warn' };
  $('#r-seg').innerHTML = ['Todos', 'Balanceo', 'Manual', 'Sistemas', 'Propios'].map(v => `<button class="${filtroCtrl === v ? 'act' : ''}" data-v="${v}">${v}</button>`).join('');
  $('#r-seg').querySelectorAll('button').forEach(b => b.onclick = () => { filtroCtrl = b.dataset.v; pintarControles(); });
  const filas = Object.entries(S.ini.codigos).filter(([c, d]) => { const p = c[0] === 'B'; return filtroCtrl === 'Todos' || (filtroCtrl === 'Propios' ? p : !p && d.resuelve === filtroCtrl); });
  $('#r-tabla').innerHTML = `<table class="tabla-s"><tr><th style="width:70px">Código</th><th style="width:200px">Campo</th><th>Control</th><th style="width:150px">Lo resuelve</th></tr>` +
    filas.map(([c, d]) => `<tr><td class="mono" style="font-weight:600">${c}</td><td class="ink2">${esc(d.campo)}</td><td>${esc(d.descripcion)}${d.validable ? '' : ' <span class="muted">(se ve con la devolución de la SSS)</span>'}</td><td>${chip(c[0] === 'B' ? 'Balidaf' : d.resuelve, c[0] === 'B' ? 'neu' : fam[d.resuelve])}</td></tr>`).join('') + '</table>';
}

// =============================================================================================
// Modales, toast y detalle de línea
// =============================================================================================
function confirmar({ titulo, texto, resumen = [], nota = '', accion = 'Aceptar', tipo = 'prim' }) {
  return new Promise(res => {
    const capa = $('#capa-modal');
    capa.innerHTML = `<div class="velo"><div class="modal"><div class="mc"><h3>${esc(titulo)}</h3><div class="mt">${esc(texto)}</div></div>
      ${resumen.length ? `<div class="res">${resumen.map(([k, v]) => `<div><span class="ink2">${esc(k)}</span><b class="${/archivo/i.test(k) ? 'mono' : ''}">${esc(v)}</b></div>`).join('')}</div>` : ''}
      ${nota ? `<div class="nota">${esc(nota)}</div>` : ''}
      <div class="mb"><button class="btn" data-r="0">Cancelar</button><button class="btn ${tipo}" data-r="1">${esc(accion)}</button></div></div></div>`;
    const fin = v => { capa.innerHTML = ''; document.removeEventListener('keydown', tecla); res(v); };
    const tecla = e => { if (e.key === 'Escape') fin(false); };
    document.addEventListener('keydown', tecla);
    capa.querySelectorAll('[data-r]').forEach(b => b.onclick = () => fin(b.dataset.r === '1'));
    capa.querySelector('.velo').onclick = e => { if (e.target.classList.contains('velo')) fin(false); };
    capa.querySelector('[data-r="1"]').focus();
  });
}
let toastT;
function toast(msg, accion) {
  const c = $('#capa-toast');
  c.innerHTML = `<div class="toast"><span class="ok">✓</span><span>${esc(msg)}</span>${accion ? `<button id="t-acc">${esc(accion[0])}</button>` : ''}<button class="x" id="t-x">×</button></div>`;
  const cerrar = () => { c.innerHTML = ''; clearTimeout(toastT); };
  $('#t-x').onclick = cerrar; if (accion) $('#t-acc').onclick = () => { cerrar(); accion[1](); };
  clearTimeout(toastT); toastT = setTimeout(cerrar, 7000);
}
async function abrirDetalle(fila) {
  const d = await api('detalle_linea', fila); if (!d || !d.fila) return;
  const g = d.grupo, capa = $('#capa-modal'), est = g ? g.estado : '';
  const fila_imp = i => { const cambia = i.p !== i.o, act = i.a !== i.o; return `<tr class="${act ? 'r-ok' : cambia ? 'r-pend' : ''}"><td>${esc(i.t)}</td><td class="mono ink2" style="font-size:12px">${esc(i.col)}</td><td class="der num">${fmt(i.o)}</td><td class="der num" style="color:var(--accent);font-weight:600">${cambia ? fmt(i.p) : ''}</td><td class="der num">${fmt(i.a)}</td></tr>`; };
  capa.innerHTML = `<div class="velo" style="padding-top:5vh"><div class="modal grande">
    <div class="dh"><div style="flex:1;min-width:0"><div class="muted" style="font-size:12px">Detalle de línea · fila ${d.fila}</div>
      <div style="display:flex;align-items:center;gap:10px;margin-top:2px"><div style="font-size:15px;font-weight:600" class="ellip">CUIL ${esc(d.cuil)} · práctica ${esc(d.cod)} · prestación ${esc(d.pres)} · clave ${esc(d.clave)}</div>
      ${est ? chip(est === 'pend' ? 'Corrección pendiente' : 'Corregida', est === 'pend' ? 'pend' : 'ok') : ''}</div></div>
      ${est === 'pend' ? `<button class="btn s prim" id="dl-act">✓ Aplicar corrección del grupo</button>` : est === 'apl' ? `<button class="btn s" id="dl-act">↶ Deshacer corrección del grupo</button>` : ''}
      <button class="cerrar" id="dl-x">×</button></div>
    <div class="dbody"><div class="st">Importes de la línea</div>
      <div class="marco"><table class="tabla-s"><tr><th>Campo</th><th>Columna Excel</th><th class="der">Original</th><th class="der">Corrección propuesta</th><th class="der">Actual (se guarda)</th></tr>${d.importes.map(fila_imp).join('')}</table></div>
      ${g ? `<div class="st">Grupo regla 624 · ${g.n} línea(s) · subsidio ${fmt(g.sub)} · corrección: ${esc(g.tipo)}</div>
      <div class="marco"><table class="tabla-s num"><tr><th>Fila</th><th>Clave</th><th class="der">Subsidiado</th><th class="der">Solicitado</th><th class="der">Aplicado original</th><th class="der">Aplicado propuesto</th><th class="der">Fdo. propios propuesto</th></tr>
      ${g.lineas.map(x => `<tr style="${x.fila === d.fila ? 'background:var(--focus-row)' : ''}"><td>${x.fila}</td><td class="mono">${esc(x.clave)}</td><td class="der">${fmt(x.sub)}</td><td class="der">${fmt(x.sol)}</td><td class="der">${fmt(x.ao)}</td><td class="der"><b>${fmt(x.ap)}</b></td><td class="der">${fmt(x.fdo)}</td></tr>`).join('')}</table></div>` : ''}
      <div class="st">Validaciones actuales de la línea (${d.validaciones.length})</div>
      ${d.validaciones.length ? `<div class="marco"><table class="tabla-s"><tr><th style="width:80px">Código</th><th style="width:120px">Nivel</th><th>Detalle</th></tr>${d.validaciones.map(v => { const f = { Error: 'err', Advertencia: 'warn', Info: 'pend' }[v.n]; return `<tr class="r-${f}"><td class="mono" style="font-weight:600">${v.c}</td><td>${chip(v.n, f)}</td><td>${esc(v.d)}</td></tr>`; }).join('')}</table></div>`
      : `<div style="color:var(--ok-fg);font-weight:600">✓ La línea cumple todas las reglas de la SSS.</div>`}
    </div></div></div>`;
  const cerrar = () => { capa.innerHTML = ''; document.removeEventListener('keydown', tecla); };
  const tecla = e => { if (e.key === 'Escape') cerrar(); };
  document.addEventListener('keydown', tecla);
  $('#dl-x').onclick = cerrar;
  capa.querySelector('.velo').onclick = e => { if (e.target.classList.contains('velo')) cerrar(); };
  if ($('#dl-act')) $('#dl-act').onclick = () => { cerrar(); est === 'pend' ? aplicar([g.id]) : deshacer([g.id]); };
}

// =============================================================================================
// Acciones
// =============================================================================================
async function examinar() { const r = await api('elegir_excel'); if (r) { S.ruta = r; pintarBalancear(); } }

async function analizarExcel() {
  const ruta = S.ruta || S.est.ruta; if (!ruta || S.ocupado) return;
  if (S.est.cambios && !await confirmar({ titulo: 'Volver a analizar', texto: 'Hay correcciones aplicadas que todavía no guardaste. Si volvés a analizar, se descartan.', nota: 'Esta acción no se puede deshacer.', accion: 'Descartar y analizar', tipo: 'peligro' })) return;
  ocupar();
  const r = await api('analizar', ruta);
  if (!r.ok) { liberar(); return alertar(r.error); }
  S.b.sel.clear(); S.b.foco = null; S.d.sel.clear(); S.d.foco = null; S.excel = null;
  S.est = Object.assign({}, S.est, { analizado: false }); seguir();
}
function ocupar() { S.ocupado = true; pintarTodo(); }
function liberar() { S.ocupado = false; pintarTodo(); }
function alertar(msg) { confirmar({ titulo: 'Balidaf', texto: msg || 'No fue posible completar la acción.', accion: 'Aceptar' }); }

async function aplicar(ids, sinConfirmar) {
  ids = (ids || []).filter(i => i !== null && i !== undefined); if (!ids.length || S.ocupado) return;
  const r = await api('resumen', ids, 'aplicar'); if (!r.grupos) return;
  if (!sinConfirmar && !await confirmar({
    titulo: 'Aplicar correcciones', accion: `Aplicar ${fn(r.grupos)}`,
    texto: 'Se modifican sólo impor_apli_sss, importe_transferido y fdo_ppio_ingre_cta_disca (y las retenciones si el subsidio no alcanza). El Excel original no se toca y podés deshacer hasta guardar.',
    resumen: [['Grupos', fn(r.grupos)], ['Líneas', fn(r.lineas)], ['Diferencia en aplicado', fmt(r.dif)]]
  })) return;
  ocupar(); const x = await api('aplicar', ids); if (!x.ok) { liberar(); return alertar(x.error); } seguir();
}
async function deshacer(ids, sinConfirmar) {
  ids = (ids || []).filter(i => i !== null && i !== undefined); if (!ids.length || S.ocupado) return;
  const r = await api('resumen', ids, 'deshacer'); if (!r.grupos) return;
  if (!sinConfirmar && !await confirmar({
    titulo: 'Deshacer correcciones', accion: `Deshacer ${fn(r.grupos)}`,
    texto: 'Los grupos vuelven a sus valores originales. La corrección queda propuesta y la podés volver a aplicar.',
    resumen: [['Grupos', fn(r.grupos)], ['Líneas', fn(r.lineas)], ['Diferencia en aplicado', fmt(-r.dif)]]
  })) return;
  ocupar(); const x = await api('deshacer', ids); if (!x.ok) { liberar(); return alertar(x.error); } seguir();
}
async function guardarExcel() {
  const e = S.est; if (!e.analizado || S.ocupado) return;
  const nota = [e.pend ? `Quedan ${fn(e.pend)} correcciones propuestas sin aplicar.` : '', e.errores ? `El Excel todavía tiene ${fn(e.errores)} errores: la SSS los va a rechazar.` : ''].filter(Boolean).join(' ');
  if (!await confirmar({
    titulo: 'Guardar Excel para Presmed', accion: 'Guardar', tipo: 'ok', nota,
    texto: 'Se guarda un Excel nuevo con las correcciones aplicadas. Sólo cambian valores: sin colores, formatos ni hojas nuevas. El original no se modifica.',
    resumen: [['Archivo', e.salida], ['Correcciones aplicadas', fn(e.apl)], ['Propuestas sin aplicar', fn(e.pend)], ['Errores a corregir a mano', fn(e.manual)]]
  })) return;
  const destino = await api('elegir_destino', 'excel'); if (!destino) return;
  ocupar(); const x = await api('guardar', destino); if (!x.ok) { liberar(); return alertar(x.error); } seguir();
}
async function exportarInforme() {
  if (!S.est.analizado || S.ocupado) return;
  const destino = await api('elegir_destino', 'informe'); if (!destino) return;
  ocupar(); const x = await api('exportar_informe', destino); if (x.ok) seguir(); else liberar();
}
async function cargarTxt(tipo) {
  if (S.ocupado) return;
  const ruta = await api('elegir_txt', tipo); if (!ruta) return;
  ocupar(); const x = await api('cargar_txt', tipo, ruta); if (!x.ok) { liberar(); return alertar(x.error); } seguir();
}
async function cambiarTema() {
  S.tema = S.tema === 'oscuro' ? 'claro' : 'oscuro';
  document.documentElement.dataset.theme = S.tema === 'oscuro' ? 'dark' : 'light';
  pintarCab(); api('tema', S.tema);
}

// ---- seguimiento de tareas en segundo plano
let siguiendo = false;
async function seguir() {
  if (siguiendo) return; siguiendo = true;
  S.ocupado = true; pintarTodo();
  for (; ;) {
    const p = await api('progreso');
    S.prog = p.prog; pintarProg();
    if (!p.ocupado) {
      S.ocupado = false; S.refrescando = true;
      await recargar();
      S.refrescando = false; siguiendo = false;
      const u = p.ultimo;
      if (u && u.t && u.t !== S.ultimoVisto) {
        S.ultimoVisto = u.t;
        if (u.tipo === 'analizar' || u.tipo === 'txt') { if (u.tipo === 'txt') irA('dev'); }
        if (u.mensaje) toast(u.mensaje, u.tipo === 'aplicar' ? ['Deshacer', () => deshacer(u.ids, true)] : u.tipo === 'deshacer' ? ['Volver a aplicar', () => aplicar(u.ids, true)] : null);
      } else if (u && u.ok === false) alertar(u.error);
      return;
    }
    await new Promise(r => setTimeout(r, 140));
  }
}
async function recargar() {
  S.est = await api('estado'); S.version = S.est.version;
  if (S.est.analizado) {
    S.grupos = await api('grupos'); S.gid = {}; S.grupos.forEach(g => S.gid[g.id] = g);
    S.cruce = S.est.cruce ? await api('cruce') : null;
  } else { S.grupos = []; S.gid = {}; S.cruce = null; }
  pintarTodo();
  if (S.tab === 'exc') cargarExcel();
}
function pintarTodo() { pintarCab(); pintarProg(); pintarTabs(); pintarBalancear(); pintarDevolucion(); pintarPie(); }

// =============================================================================================
// Inicio
// =============================================================================================
(async function () {
  await listo();
  S.ini = await api('inicio');
  S.tema = S.ini.tema || 'claro';
  document.documentElement.dataset.theme = S.tema === 'oscuro' ? 'dark' : 'light';
  armarBalancear(); armarDevolucion(); armarExcel(); armarReglas();
  irA('bal');
  await recargar();
  const p = await api('progreso'); if (p.ocupado) seguir();
  window.__balidafListo = true;
})();
