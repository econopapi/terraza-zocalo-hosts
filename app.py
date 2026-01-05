from flask import Flask, render_template, request, jsonify, redirect, url_for
from models import db, Equipo, Host, Mesero, RegistroDiarioHosteo, CorteDiarioHosteo
from config import Config
from datetime import datetime, date
from sqlalchemy import func
from zoneinfo import ZoneInfo

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def get_cdmx_time():
    return datetime.now(ZoneInfo("America/Mexico_City"))


@app.route('/')
def index():
    response_payload = jsonify({
        "mensaje": "Terraza Zócalo - Sistema de registro de Hosteos",
        "autor": "Daniel Limón <dani@dlimon.net>",
        "rutas_disponibles": {
            "/equipo-<int:equipo_id>": "Formulario para registrar hosteos por equipo",
            "/reporte/<int:equipo_id>": "Reporte diario de hosteos por equipo"
        }
    })
    return response_payload
    
@app.route('/equipo/<int:equipo_id>', methods=['GET', 'POST'])
def equipo_form(equipo_id):
    equipo = Equipo.query.get_or_404(equipo_id)
    hosts = Host.query.filter_by(id_equipo=equipo_id).all()
    meseros = Mesero.query.all()
    
    if request.method == 'POST':
        registro = RegistroDiarioHosteo(
            id_host=request.form.get('id_host'),
            numero_personas=request.form.get('numero_personas'),
            id_mesero=request.form.get('id_mesero'),
            confirmada=False
        )
        db.session.add(registro)
        db.session.commit()
        return redirect(url_for('equipo_form', equipo_id=equipo_id))
    
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
                         registros=registros)

@app.route('/api/confirmar/<int:registro_id>', methods=['POST'])
def confirmar_registro(registro_id):
    registro = RegistroDiarioHosteo.query.get_or_404(registro_id)
    data = request.get_json()
    registro.confirmada = data.get('confirmada', False)
    db.session.commit()
    return jsonify({'success': True, 'confirmada': registro.confirmada})

@app.route('/reporte/<int:equipo_id>')
def reporte_equipo(equipo_id):
    equipo = Equipo.query.get_or_404(equipo_id)
    fecha_param = request.args.get('fecha')
    
    if fecha_param:
        try:
            fecha_reporte = datetime.strptime(fecha_param, '%Y-%m-%d').date()
        except:
            fecha_reporte = get_cdmx_time().date()
    else:
        fecha_reporte = get_cdmx_time().date()
    
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
        func.sum(RegistroDiarioHosteo.numero_personas).label('personas')
    ).join(RegistroDiarioHosteo).filter(
        Host.id_equipo == equipo_id,
        RegistroDiarioHosteo.fecha == fecha_reporte
    ).group_by(Host.nombre_host, Host.id_host).order_by(func.count(RegistroDiarioHosteo.id_registro_hosteo).desc()).all()
    
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

@app.route('/reporte/<int:equipo_id>/host/<int:host_id>')
def reporte_host(equipo_id, host_id):
    equipo = Equipo.query.get_or_404(equipo_id)
    host = Host.query.get_or_404(host_id)
    fecha_param = request.args.get('fecha')
    
    if fecha_param:
        try:
            fecha_reporte = datetime.strptime(fecha_param, '%Y-%m-%d').date()
        except:
            fecha_reporte = get_cdmx_time().date()
    else:
        fecha_reporte = get_cdmx_time().date()
    
    # Registros del host específico en la fecha seleccionada
    registros = RegistroDiarioHosteo.query.filter(
        RegistroDiarioHosteo.id_host == host_id,
        RegistroDiarioHosteo.fecha == fecha_reporte
    ).order_by(RegistroDiarioHosteo.hora.desc()).all()
    
    total_hosteos = len(registros)
    confirmados = sum(1 for r in registros if r.confirmada)
    no_confirmados = total_hosteos - confirmados
    total_personas = sum(r.numero_personas for r in registros)
    personas_confirmadas = sum(r.numero_personas for r in registros if r.confirmada)
    
    print(f"DEBUG - Host: {host.nombre_host}, Fecha: {fecha_reporte}, Total: {total_hosteos}")
    
    return render_template('reporte_host.html',
                         equipo=equipo,
                         host=host,
                         total_hosteos=total_hosteos,
                         confirmados=confirmados,
                         no_confirmados=no_confirmados,
                         total_personas=total_personas,
                         personas_confirmadas=personas_confirmadas,
                         registros=registros,
                         fecha_reporte=fecha_reporte.isoformat())

# Script para inicializar DB con datos de prueba
@app.cli.command()
def init_db():
    """Inicializa la base de datos con datos de ejemplo"""
    db.create_all()
    
    # Crear equipos
    equipos = [
        Equipo(id_equipo=1, lider_equipo='Ana García'),
        Equipo(id_equipo=2, lider_equipo='Carlos Ruiz'),
        Equipo(id_equipo=3, lider_equipo='María López'),
        Equipo(id_equipo=4, lider_equipo='Juan Pérez')
    ]
    db.session.add_all(equipos)
    
    # Crear hosts
    hosts = [
        Host(id_equipo=1, nombre_host='Laura'),
        Host(id_equipo=1, nombre_host='Pedro'),
        Host(id_equipo=2, nombre_host='Sofia'),
        Host(id_equipo=2, nombre_host='Diego'),
        Host(id_equipo=3, nombre_host='Valeria'),
        Host(id_equipo=3, nombre_host='Andrés'),
        Host(id_equipo=4, nombre_host='Camila'),
        Host(id_equipo=4, nombre_host='Roberto'),
    ]
    db.session.add_all(hosts)
    
    # Crear meseros
    meseros = [
        Mesero(nombre_mesero='Mesero 1'),
        Mesero(nombre_mesero='Mesero 2'),
        Mesero(nombre_mesero='Mesero 3'),
        Mesero(nombre_mesero='Mesero 4'),
        Mesero(nombre_mesero='Mesero 5'),
    ]
    db.session.add_all(meseros)
    
    db.session.commit()
    print('✅ Base de datos inicializada con éxito')

if __name__ == '__main__':
    app.run(debug=True)