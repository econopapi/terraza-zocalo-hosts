from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from zoneinfo import ZoneInfo


db = SQLAlchemy()

class Equipo(db.Model):
    __tablename__ = 'equipos'
    
    id_equipo = db.Column(db.Integer, primary_key=True)
    lider_equipo = db.Column(db.String(100), nullable=False)
    hosts = db.relationship('Host', backref='equipo', lazy=True)
    cortes = db.relationship('CorteDiarioHosteo', backref='equipo', lazy=True)

class Host(db.Model):
    __tablename__ = 'hosts'
    
    id_host = db.Column(db.Integer, primary_key=True)
    id_equipo = db.Column(db.Integer, db.ForeignKey('equipos.id_equipo'), nullable=False)
    nombre_host = db.Column(db.String(100), nullable=False)
    
    registros = db.relationship('RegistroDiarioHosteo', backref='host', lazy=True)

class Mesero(db.Model):
    __tablename__ = 'meseros'
    
    id_mesero = db.Column(db.Integer, primary_key=True)
    nombre_mesero = db.Column(db.String(100), nullable=False)
    
    registros = db.relationship('RegistroDiarioHosteo', backref='mesero', lazy=True)

class RegistroDiarioHosteo(db.Model):
    __tablename__ = 'registro_diario_hosteos'
    
    id_registro_hosteo = db.Column(db.Integer, primary_key=True)
    id_host = db.Column(db.Integer, db.ForeignKey('hosts.id_host'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    numero_personas = db.Column(db.Integer, nullable=False)
    id_mesero = db.Column(db.Integer, db.ForeignKey('meseros.id_mesero'), nullable=False)
    confirmada = db.Column(db.Boolean, default=False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.fecha or not self.hora:
            now = datetime.now(ZoneInfo("America/Mexico_City"))
            self.fecha = now.date()
            self.hora = now.time()


class CorteDiarioHosteo(db.Model):
    __tablename__ = 'corte_diario_hosteos'
    
    id_corte_hosteo = db.Column(db.Integer, primary_key=True)
    id_equipo = db.Column(db.Integer, db.ForeignKey('equipos.id_equipo'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    px_totales = db.Column(db.Integer, default=0)
    px_bajadas = db.Column(db.Integer, default=0)
    px_quedadas = db.Column(db.Integer, default=0)
    mesas_totales = db.Column(db.Integer, default=0)
    mesas_bajadas = db.Column(db.Integer, default=0)
    mesas_quedadas = db.Column(db.Integer, default=0)
    total_mxn = db.Column(db.Float, default=0.0)