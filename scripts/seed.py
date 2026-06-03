import json
import os
import sys

# Adiciona o diretório src ao path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from database import SessionLocal, Vehicle, init_db

def seed():
    # Inicializa o banco de dados
    init_db()
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CARS_JSON_PATH = os.path.join(BASE_DIR, "data", "cars.json")
    
    db = SessionLocal()
    try:
        print(f"Sincronizando a tabela de veículos com o arquivo {CARS_JSON_PATH}...")
        if not os.path.exists(CARS_JSON_PATH):
            print(f"Erro: Arquivo {CARS_JSON_PATH} não encontrado.")
            return

        with open(CARS_JSON_PATH, "r", encoding="utf-8") as f:
            cars_data = json.load(f)
        
        added_count = 0
        for car in cars_data:
            exists = db.query(Vehicle).filter(
                Vehicle.brand == car["brand"],
                Vehicle.model == car["model"],
                Vehicle.year == car["year"]
            ).first()
            
            if not exists:
                db_car = Vehicle(
                    brand=car["brand"],
                    model=car["model"],
                    year=car["year"],
                    battery_kwh=car["battery_kwh"],
                    max_ac_kw=car["max_ac_kw"],
                    max_dc_kw=car["max_dc_kw"]
                )
                db.add(db_car)
                added_count += 1
        
        db.commit()
        if added_count > 0:
            print(f"{added_count} novos veículos inseridos com sucesso.")
        else:
            print("Nenhum novo veículo para adicionar.")
            
    except Exception as e:
        print(f"Erro ao executar o seed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
