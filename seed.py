import json
from main import SessionLocal, Vehicle, init_db

def seed():
    # Inicializa o banco de dados (cria as tabelas se não existirem)
    init_db()
    
    db = SessionLocal()
    try:
        print("Sincronizando a tabela de veículos com o arquivo cars.json...")
        with open("cars.json", "r", encoding="utf-8") as f:
            cars_data = json.load(f)
        
        added_count = 0
        for car in cars_data:
            # Verifica se o veículo já existe (mesma marca, modelo e ano)
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
