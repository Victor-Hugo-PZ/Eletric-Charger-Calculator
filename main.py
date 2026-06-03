from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, Session, declarative_base
from pydantic import BaseModel
from typing import List, Dict

# Configuração do Banco de Dados
SQLALCHEMY_DATABASE_URL = "sqlite:///./charger_time.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelos do Banco de Dados
class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String)
    model = Column(String)
    year = Column(Integer)
    battery_kwh = Column(Float)
    max_ac_kw = Column(Float)
    max_dc_kw = Column(Float)
    simulations = relationship("Simulation", back_populates="vehicle")

    def to_dict(self):
        return {
            "id": self.id,
            "brand": self.brand,
            "model": self.model,
            "year": self.year,
            "battery_kwh": self.battery_kwh,
            "max_ac_kw": self.max_ac_kw,
            "max_dc_kw": self.max_dc_kw
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
    Base.metadata.create_all(bind=engine)

# App FastAPI
app = FastAPI(title="Charger Time API")

# Inicializa o banco de dados
init_db()

# Servir arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Schemas
class SimulationRequest(BaseModel):
    car_id: int
    porcentagem_bateria_atual: float
    porcentagem_bateria_desejada: float
    potencia_carregador_kw: float
    tarifa_kwh_reais: float

class SimulationResponse(BaseModel):
    total_time_minutes: float
    total_cost: float
    energy_added_kwh: float

@app.get("/api/cars")
def get_cars(db: Session = Depends(get_db)):
    vehicles = db.query(Vehicle).all()
    return [v.to_dict() for v in vehicles]

@app.post("/api/simulate", response_model=SimulationResponse)
def simulate(request: SimulationRequest, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == request.car_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")

    if request.porcentagem_bateria_atual >= request.porcentagem_bateria_desejada:
        return SimulationResponse(total_time_minutes=0, total_cost=0, energy_added_kwh=0)

    # Determinar se o carregador é AC ou DC
    # AC <= 22kW, DC > 22kW
    if request.potencia_carregador_kw <= 22:
        vehicle_max_power = vehicle.max_ac_kw
    else:
        vehicle_max_power = vehicle.max_dc_kw

    if vehicle_max_power == 0:
        raise HTTPException(status_code=400, detail="Veículo não suporta este tipo de carregador")

    battery_capacity = vehicle.battery_kwh
    initial_soc = request.porcentagem_bateria_atual
    final_soc = request.porcentagem_bateria_desejada

    total_time_hours = 0
    energy_total = 0

    # Fase 1: Até 80%
    if initial_soc < 80:
        soc_end_phase1 = min(80, final_soc)
        energy_phase1 = (soc_end_phase1 - initial_soc) / 100 * battery_capacity
        power_phase1 = min(request.potencia_carregador_kw, vehicle_max_power)
        
        if power_phase1 > 0:
            total_time_hours += energy_phase1 / power_phase1
            energy_total += energy_phase1

    # Fase 2: De 80% a 100%
    if final_soc > 80:
        soc_start_phase2 = max(80, initial_soc)
        energy_phase2 = (final_soc - soc_start_phase2) / 100 * battery_capacity
        # A potência despenca para 20% da potência máxima aceita
        power_phase2 = 0.2 * vehicle_max_power
        
        if power_phase2 > 0:
            total_time_hours += energy_phase2 / power_phase2
            energy_total += energy_phase2

    total_time_minutes = total_time_hours * 60
    total_cost = energy_total * request.tarifa_kwh_reais

    # Salvar no histórico
    db_simulation = Simulation(
        vehicle_id=vehicle.id,
        initial_soc_percent=initial_soc,
        final_soc_percent=final_soc,
        charger_power_kw=request.potencia_carregador_kw,
        total_time_minutes=total_time_minutes,
        total_cost=total_cost
    )
    db.add(db_simulation)
    db.commit()

    return SimulationResponse(
        total_time_minutes=round(total_time_minutes, 2),
        total_cost=round(total_cost, 2),
        energy_added_kwh=round(energy_total, 2)
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
