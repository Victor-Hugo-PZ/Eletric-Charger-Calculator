from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, Session, declarative_base
import os

# Caminho absoluto para o banco de dados na pasta data/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "charger_time.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String)
    model = Column(String)
    year = Column(Integer)
    battery_kwh = Column(Float)
    max_ac_kw = Column(Float)
    max_dc_kw = Column(Float)
    range_km = Column(Float)
    power_hp = Column(Integer)
    drive = Column(String)
    seats = Column(Integer)
    body = Column(String)
    weight_kg = Column(Integer)
    country_of_origin = Column(String)
    connector_ac = Column(String)
    connector_dc = Column(String)
    type = Column(String)
    simulations = relationship("Simulation", back_populates="vehicle")

    def to_dict(self):
        return {
            "id": self.id,
            "brand": self.brand,
            "model": self.model,
            "year": self.year,
            "battery_kwh": self.battery_kwh,
            "max_ac_kw": self.max_ac_kw,
            "max_dc_kw": self.max_dc_kw,
            "range_km": self.range_km,
            "power_hp": self.power_hp,
            "drive": self.drive,
            "seats": self.seats,
            "body": self.body,
            "weight_kg": self.weight_kg,
            "country_of_origin": self.country_of_origin,
            "connector_ac": self.connector_ac,
            "connector_dc": self.connector_dc,
            "type": self.type
        }

class Simulation(Base):
    __tablename__ = "simulations"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    initial_soc_percent = Column(Float)
    final_soc_percent = Column(Float)
    charger_power_kw = Column(Float)
    total_time_minutes = Column(Float)
    total_cost = Column(Float)
    vehicle = relationship("Vehicle", back_populates="simulations")

def init_db():
    # Garante que a pasta data existe
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(bind=engine)