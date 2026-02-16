import secrets
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.config.database import SessionLocal
from app.models.system import System

def seed_systems():
    # Ensure tables exist
    from app.config.database import engine, Base
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        systems_to_seed = [
            {"id": 1, "name": "Intelligence", "base_url": "https://digital.sbacem.com.br"},
            {"id": 2, "name": "CRM", "base_url": "https://conversor.sbacem.app.br"},
            {"id": 3, "name": "Sistema Cadastro", "base_url": "http://amplo.app.br"},
            {"id": 4, "name": "Fonogramas", "base_url": "http://fonogramas.sbacem.app.br"},
        ]

        for sys_data in systems_to_seed:
            existing = db.query(System).filter(System.id == sys_data["id"]).first()
            if existing:
                print(f"Updating system: {sys_data['name']}")
                existing.name = sys_data["name"]
                existing.base_url = sys_data["base_url"]
            else:
                print(f"Creating system: {sys_data['name']}")
                new_system = System(
                    id=sys_data["id"],
                    name=sys_data["name"],
                    base_url=sys_data["base_url"],
                    secret_key=secrets.token_hex(32)
                )
                db.add(new_system)
        
        db.commit()
        print("Seeding completed successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding systems: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_systems()
