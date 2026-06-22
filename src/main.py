from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uvicorn
import os
import sys

# Adiciona o diretório src ao path para permitir imports relativos se necessário
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, Vehicle, Simulation, init_db

app = FastAPI(title="Charger Time API")

# Inicializa o banco de dados
init_db()

# Caminhos absolutos para arquivos estáticos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Servir arquivos estáticos
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

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
    range_added_km: float

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
        power_phase2 = 0.2 * vehicle_max_power
        
        if power_phase2 > 0:
            total_time_hours += energy_phase2 / power_phase2
            energy_total += energy_phase2

    total_time_minutes = total_time_hours * 60
    total_cost = energy_total * request.tarifa_kwh_reais

    # Calculate range added
    if vehicle.range_km and vehicle.range_km > 0:
        if request.porcentagem_bateria_atual >= request.porcentagem_bateria_desejada:
            range_added_km = 0
        else:
            range_added_km = ((request.porcentagem_bateria_desejada - request.porcentagem_bateria_atual) / 100) * vehicle.range_km
            range_added_km = round(range_added_km)
    else:
        range_added_km = 0

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
        energy_added_kwh=round(energy_total, 2),
        range_added_km=range_added_km
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
