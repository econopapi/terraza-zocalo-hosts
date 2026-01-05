from flask import Flask, render_template, request, jsonify, redirect, url_for
from models import db, Equipo, Host, Mesero, RegistroDiarioHosteo, CorteDiarioHosteo
from config import Config
from datetime import datetime, date
from sqlalchemy import func
from zoneinfo import ZoneInfo
from flask import render_template_string

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def get_cdmx_time():
    return datetime.now(ZoneInfo("America/Mexico_City"))

# NEW: helpers to pick latest date with data
def get_latest_fecha_equipo(equipo_id):
    return db.session.query(func.max(RegistroDiarioHosteo.fecha))\
        .join(Host, RegistroDiarioHosteo.id_host == Host.id_host)\
        .filter(Host.id_equipo == equipo_id).scalar()

def get_latest_fecha_mesero(mesero_id):
    return db.session.query(func.max(RegistroDiarioHosteo.fecha))\
        .filter(RegistroDiarioHosteo.id_mesero == mesero_id).scalar()

def get_latest_fecha_global():
    return db.session.query(func.max(RegistroDiarioHosteo.fecha)).scalar()

@app.route('/')
def index():
    # Landing page with three role buttons and prompt-based key entry
    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Inicio{% endblock %}
    {% block content %}
    <div class="header">
        <h1>Bienvenido</h1>
        <p>Selecciona una opción</p>
        <div class="no-print" style="margin-top:10px;">
            <button class="btn" onclick="goHost()">Hosteos</button>
            <button class="btn" onclick="goMesero()">Meseros</button>
            <button class="btn" onclick="goReportes()">Reportes</button>
        </div>
    </div>
    {% endblock %}
    {% block scripts %}
    <script>
    function goHost(){
        const clave = prompt('Clave de host');
        if (!clave) return;
        fetch(`/access/host?clave=${encodeURIComponent(clave)}`)
        .then(r => r.json()).then(d => {
            if (d.success) {
                window.location.href = `/equipo/${d.id_equipo}?host_id=${d.id_host}`;
            } else {
                alert(d.error || 'Clave inválida');
            }
        });
    }
    function goMesero(){
        const clave = prompt('Clave de mesero');
        if (!clave) return;
        fetch(`/access/mesero?clave=${encodeURIComponent(clave)}`)
        .then(r => r.json()).then(d => {
            if (d.success) {
                const today = new Date().toISOString().split('T')[0];
                window.location.href = `/mesero/${d.id_mesero}?fecha=${today}&clave=${encodeURIComponent(clave)}`;
            } else {
                alert(d.error || 'Clave inválida');
            }
        });
    }
    function goReportes(){
        const clave = prompt('Clave de líder');
        if (!clave) return;
        fetch(`/access/lider?clave=${encodeURIComponent(clave)}`)
        .then(r => r.json()).then(d => {
            if (d.success) {
                const today = new Date().toISOString().split('T')[0];
                if (d.id_equipo == 777) {
                    window.location.href = `/reporte-total?fecha=${today}`;
                } else {
                    window.location.href = `/reporte/${d.id_equipo}?fecha=${today}`;
                }
            } else {
                alert(d.error || 'Clave inválida');
            }
        });
    }
    </script>
    {% endblock %}
    """)

@app.route('/access/host')
def access_host():
    clave = request.args.get('clave', '').strip()
    host = Host.query.filter_by(clave_host=clave).first()
    if not host:
        return jsonify(success=False, error='Clave de host inválida'), 404
    return jsonify(success=True, id_equipo=host.id_equipo, id_host=host.id_host)

@app.route('/access/mesero')
def access_mesero():
    clave = request.args.get('clave', '').strip()
    mesero = Mesero.query.filter_by(clave_mesero=clave).first()
    if not mesero:
        return jsonify(success=False, error='Clave de mesero inválida'), 404
    return jsonify(success=True, id_mesero=mesero.id_mesero)

@app.route('/access/lider')
def access_lider():
    clave = request.args.get('clave', '').strip()
    equipo = Equipo.query.filter_by(clave_lider=clave).first()
    if not equipo:
        return jsonify(success=False, error='Clave de líder inválida'), 404
    return jsonify(success=True, id_equipo=equipo.id_equipo)

@app.route('/equipo/<int:equipo_id>', methods=['GET', 'POST'])
def equipo_form(equipo_id):
    equipo = Equipo.query.get_or_404(equipo_id)
    hosts = Host.query.filter_by(id_equipo=equipo_id).all()
    meseros = Mesero.query.all()
    locked_host_id = request.args.get('host_id', type=int)
    locked_host = Host.query.get(locked_host_id) if locked_host_id else None
    if locked_host and locked_host.id_equipo != equipo_id:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Enforce locked host if present
        id_host = locked_host.id_host if locked_host else request.form.get('id_host')
        # Validate host belongs to equipo
        host_obj = Host.query.get_or_404(int(id_host))
        if host_obj.id_equipo != equipo_id:
            return redirect(url_for('index'))
        registro = RegistroDiarioHosteo(
            id_host=id_host,
            numero_personas=request.form.get('numero_personas'),
            id_mesero=request.form.get('id_mesero'),
            confirmada=False
        )
        db.session.add(registro)
        db.session.commit()
        return redirect(url_for('equipo_form', equipo_id=equipo_id, host_id=locked_host_id) if locked_host_id else url_for('equipo_form', equipo_id=equipo_id))
    
    # Registros del día
    hoy = get_cdmx_time().date()
    registros = RegistroDiarioHosteo.query.join(Host).filter(
        Host.id_equipo == equipo_id,
        RegistroDiarioHosteo.fecha == hoy
    ).order_by(RegistroDiarioHosteo.hora.desc()).all()
    
    return render_template('equipo.html', 
                         equipo=equipo, 
                         hosts=hosts, 
                         meseros=meseros,
                         registros=registros,
                         locked_host=locked_host)

@app.route('/api/confirmar/<int:registro_id>', methods=['POST'])
def confirmar_registro(registro_id):
    registro = RegistroDiarioHosteo.query.get_or_404(registro_id)
    data = request.get_json() or {}
    # Enforce: only assigned mesero with valid clave can confirm
    mesero_clave = data.get('mesero_clave')
    mesero = Mesero.query.filter_by(clave_mesero=mesero_clave).first()
    if not mesero or mesero.id_mesero != registro.id_mesero:
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    registro.confirmada = data.get('confirmada', False)
    db.session.commit()
    return jsonify({'success': True, 'confirmada': registro.confirmada})

@app.route('/mesero/<int:mesero_id>')
def vista_mesero(mesero_id):
    # Require clave param to view
    clave = request.args.get('clave', '').strip()
    mesero = Mesero.query.get_or_404(mesero_id)
    if not mesero.clave_mesero or mesero.clave_mesero != clave:
        return "No autorizado", 403

    fecha_param = request.args.get('fecha')
    if fecha_param:
        try:
            fecha_reporte = datetime.strptime(fecha_param, '%Y-%m-%d').date()
        except:
            # fallback to latest for this mesero
            fecha_reporte = get_latest_fecha_mesero(mesero_id) or get_cdmx_time().date()
    else:
        # default to latest date with data for this mesero
        fecha_reporte = get_latest_fecha_mesero(mesero_id) or get_cdmx_time().date()

    registros = RegistroDiarioHosteo.query.filter(
        RegistroDiarioHosteo.id_mesero == mesero_id,
        RegistroDiarioHosteo.fecha == fecha_reporte
    ).order_by(RegistroDiarioHosteo.hora.desc()).all()

    total_hosteos = len(registros)
    confirmados = sum(1 for r in registros if r.confirmada)
    no_confirmados = total_hosteos - confirmados
    total_personas = sum(r.numero_personas for r in registros)
    personas_confirmadas = sum(r.numero_personas for r in registros if r.confirmada)

    # Render lightweight view reusing table UX
    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Mesero {{ mesero.nombre_mesero }}{% endblock %}
    {% block content %}
    <div class="breadcrumb no-print"><a href="{{ url_for('index') }}">← Inicio</a></div>
    <div class="header">
        <h1>Registros de Hoy - Mesero {{ mesero.nombre_mesero }}</h1>
        <p>Fecha: {{ fecha_reporte }}</p>
    </div>
    <div class="form-card no-print">
        <div class="fecha-selector">
            <label for="fecha-input">Selecciona una fecha:</label>
            <input type="date" id="fecha-input" value="{{ fecha_reporte }}">
            <button onclick="filtrarPorFecha()">🔍 Filtrar</button>
            <button onclick="irAHoy()" class="btn btn-hoy">📅 Ir a Hoy</button>
        </div>
    </div>
    <div class="stats-grid">
        <div class="stat-card"><div class="stat-label">👥 Total Personas</div><div class="stat-value">{{ total_personas }}</div></div>
        <div class="stat-card"><div class="stat-label">✅ Personas Confirmadas</div><div class="stat-value">{{ personas_confirmadas }}</div></div>
        <div class="stat-card"><div class="stat-label">🍽️ Total Mesas</div><div class="stat-value">{{ total_hosteos }}</div></div>
        <div class="stat-card"><div class="stat-label">✅ Mesas Confirmadas</div><div class="stat-value">{{ confirmados }}</div></div>
        <div class="stat-card"><div class="stat-label">❌ Mesas No Confirmadas</div><div class="stat-value">{{ no_confirmados }}</div></div>
    </div>
    <div class="form-card">
        <h2>Registros del Mesero</h2>
        {% if registros %}
        <div class="table-wrapper">
            <table>
                <thead><tr>
                    <th>Hora</th>
                    <th>Equipo</th>
                    <th>Host</th>
                    <th>Personas</th>
                    <th>Confirmado</th>
                </tr></thead>
                <tbody>
                {% for r in registros %}
                    <tr>
                        <td>{{ r.hora.strftime('%H:%M') }}</td>
                        <td>{{ r.host.equipo.id_equipo if r.host and r.host.equipo else 'N/D' }}</td>
                        <td>{{ r.host.nombre_host if r.host else 'N/D' }}</td>
                        <td>{{ r.numero_personas }}</td>
                        <td>
                            <button type="button" class="status-btn" data-registro-id="{{ r.id_registro_hosteo }}" onclick="toggleConfirmacion(this)">
                                <span class="{% if r.confirmada %}confirmada{% else %}no-confirmada{% endif %}">
                                    {% if r.confirmada %}✅{% else %}❌{% endif %}
                                </span>
                            </button>
                        </td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
        <p style="text-align:center;color:#999;padding:20px;">Sin registros para esta fecha</p>
        {% endif %}
    </div>
    {% endblock %}
    {% block scripts %}
    <script>
    function filtrarPorFecha(){
        const fecha = document.getElementById('fecha-input').value;
        const clave = encodeURIComponent('{{ clave }}');
        window.location.href = `/mesero/{{ mesero.id_mesero }}?fecha=${fecha}&clave=${clave}`;
    }
    function irAHoy(){
        const today = new Date().toISOString().split('T')[0];
        const clave = encodeURIComponent('{{ clave }}');
        window.location.href = `/mesero/{{ mesero.id_mesero }}?fecha=${today}&clave=${clave}`;
    }
    function toggleConfirmacion(btn){
        const registroId = btn.dataset.registroId;
        const span = btn.querySelector('span');
        const isConfirmada = span.classList.contains('confirmada');
        const nuevaConfirmacion = !isConfirmada;
        fetch(`/api/confirmar/${encodeURIComponent(registroId)}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({confirmada: nuevaConfirmacion, mesero_clave: '{{ clave }}'})
        })
        .then(r=>r.json())
        .then(data=>{
            if (data.success) {
                span.textContent = data.confirmada ? '✅' : '❌';
                span.className = data.confirmada ? 'confirmada' : 'no-confirmada';
            } else {
                alert(data.error || 'No autorizado');
            }
        })
        .catch(err=>console.error('Error confirmación:', err));
    }
    </script>
    {% endblock %}
    """, mesero=mesero, registros=registros,
       total_hosteos=total_hosteos, confirmados=confirmados,
       no_confirmados=no_confirmados, total_personas=total_personas,
       personas_confirmadas=personas_confirmadas, fecha_reporte=fecha_reporte.isoformat(),
       clave=clave)

@app.route('/reporte/<int:equipo_id>')
def reporte_equipo(equipo_id):
    equipo = Equipo.query.get_or_404(equipo_id)
    fecha_param = request.args.get('fecha')
    
    if fecha_param:
        try:
            fecha_reporte = datetime.strptime(fecha_param, '%Y-%m-%d').date()
        except:
            fecha_reporte = get_latest_fecha_equipo(equipo_id) or get_cdmx_time().date()
    else:
        # default to latest date with data for this equipo
        fecha_reporte = get_latest_fecha_equipo(equipo_id) or get_cdmx_time().date()
    
    # Registros del día seleccionado con ordenamiento
    registros = RegistroDiarioHosteo.query.join(Host).filter(
        Host.id_equipo == equipo_id,
        RegistroDiarioHosteo.fecha == fecha_reporte
    ).order_by(RegistroDiarioHosteo.hora.desc()).all()
    
    total_hosteos = len(registros)
    confirmados = sum(1 for r in registros if r.confirmada)
    no_confirmados = total_hosteos - confirmados
    total_personas = sum(r.numero_personas for r in registros)
    personas_confirmadas = sum(r.numero_personas for r in registros if r.confirmada)
    
    # Ranking de hosts
    ranking = db.session.query(
        Host.nombre_host,
        Host.id_host,
        func.count(RegistroDiarioHosteo.id_registro_hosteo).label('total'),
        func.sum(RegistroDiarioHosteo.numero_personas).label('personas'),
        Host.id_equipo.label('host_equipo_id')
    ).join(RegistroDiarioHosteo).filter(
        Host.id_equipo == equipo_id,
        RegistroDiarioHosteo.fecha == fecha_reporte
    ).group_by(Host.nombre_host, Host.id_host, Host.id_equipo)\
     .order_by(func.count(RegistroDiarioHosteo.id_registro_hosteo).desc()).all()
    
    print(f"DEBUG - Equipo: {equipo.id_equipo}, Fecha: {fecha_reporte}, Total hosteos: {total_hosteos}")
    
    return render_template('reporte.html',
                         equipo=equipo,
                         total_hosteos=total_hosteos,
                         confirmados=confirmados,
                         no_confirmados=no_confirmados,
                         total_personas=total_personas,
                         personas_confirmadas=personas_confirmadas,
                         ranking=ranking,
                         registros=registros,
                         fecha_reporte=fecha_reporte.isoformat())

@app.route('/reporte-total')
def reporte_total():
    # Aggregate report across all equipos; uses same template with Equipo: id 777
    fecha_param = request.args.get('fecha')
    if fecha_param:
        try:
            fecha_reporte = datetime.strptime(fecha_param, '%Y-%m-%d').date()
        except:
            fecha_reporte = get_latest_fecha_global() or get_cdmx_time().date()
    else:
        # default to latest date with data (global)
        fecha_reporte = get_latest_fecha_global() or get_cdmx_time().date()

    registros = RegistroDiarioHosteo.query.filter(
        RegistroDiarioHosteo.fecha == fecha_reporte
    ).order_by(RegistroDiarioHosteo.hora.desc()).all()

    total_hosteos = len(registros)
    confirmados = sum(1 for r in registros if r.confirmada)
    no_confirmados = total_hosteos - confirmados
    total_personas = sum(r.numero_personas for r in registros)
    personas_confirmadas = sum(r.numero_personas for r in registros if r.confirmada)

    ranking = db.session.query(
        Host.nombre_host,
        Host.id_host,
        func.count(RegistroDiarioHosteo.id_registro_hosteo).label('total'),
        func.sum(RegistroDiarioHosteo.numero_personas).label('personas'),
        Host.id_equipo.label('host_equipo_id')
    ).join(RegistroDiarioHosteo).filter(
        RegistroDiarioHosteo.fecha == fecha_reporte
    ).group_by(Host.nombre_host, Host.id_host, Host.id_equipo)\
     .order_by(func.count(RegistroDiarioHosteo.id_registro_hosteo).desc()).all()

    equipo_control = Equipo.query.get(777)
    return render_template('reporte.html',
                         equipo=equipo_control,
                         total_hosteos=total_hosteos,
                         confirmados=confirmados,
                         no_confirmados=no_confirmados,
                         total_personas=total_personas,
                         personas_confirmadas=personas_confirmadas,
                         ranking=ranking,
                         registros=registros,
                         fecha_reporte=fecha_reporte.isoformat())

# Script para inicializar DB con datos de prueba
@app.cli.command()
def init_db():
    """Inicializa la base de datos con datos de ejemplo"""
    db.create_all()
    
    # Crear equipos
    equipos = [
        Equipo(id_equipo=1, lider_equipo='Ana García', clave_lider='julio2026'),
        Equipo(id_equipo=2, lider_equipo='Carlos Ruiz', clave_lider='luis2026'),
        Equipo(id_equipo=3, lider_equipo='María López', clave_lider='joel2026'),
        Equipo(id_equipo=4, lider_equipo='Juan Pérez', clave_lider='gordo2026'),
        Equipo(id_equipo=777, lider_equipo='Control', clave_lider='control2026'),
    ]
    db.session.add_all(equipos)
    
    # Crear hosts
    hosts = [
        Host(id_equipo=1, nombre_host='Yasmin', clave_host='host2026yasmin'),
        Host(id_equipo=1, nombre_host='Karo', clave_host='host2026karo'),
        Host(id_equipo=1, nombre_host='Diego', clave_host='host2026diego'),
        Host(id_equipo=1, nombre_host='Julio', clave_host='host2026julio'),
        Host(id_equipo=2, nombre_host='Daniela', clave_host='host2026daniela'),
        Host(id_equipo=2, nombre_host='Antony', clave_host='host2026antony'),
    ]
    db.session.add_all(hosts)
    
    # Crear meseros
    meseros = [
        Mesero(nombre_mesero='Julio', clave_mesero='mesero2026julio'),
        Mesero(nombre_mesero='Yaky', clave_mesero='mesero2026yaky'),
        Mesero(nombre_mesero='Rosaura', clave_mesero='mesero2026rosaura'),
        Mesero(nombre_mesero='Karen', clave_mesero='mesero2026karen'),
        Mesero(nombre_mesero='Mónica', clave_mesero='mesero2026monica'),
        Mesero(nombre_mesero='Ana', clave_mesero='mesero2026ana'),
        Mesero(nombre_mesero='Jatt', clave_mesero='mesero2026jatt'),
    ]
    db.session.add_all(meseros)
    
    db.session.commit()
    print('✅ Base de datos inicializada con éxito')

if __name__ == '__main__':
    app.run(debug=True)