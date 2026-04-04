from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

SQLALCHEMY_DATABASE_URL = "sqlite:///./fellah_ai.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 1. Table des Diagnostics (Images)
class DiagnosticRecord(Base):
    __tablename__ = "diagnostics"
    id = Column(Integer, primary_key=True, index=True)
    farmer_phone = Column(String)
    disease_detected = Column(String)
    confidence_score = Column(Float)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

# 2. Table des Profils Agriculteurs (Persistance)
class FarmerProfile(Base):
    __tablename__ = "farmer_profiles"
    phone = Column(String, primary_key=True)
    region = Column(String, nullable=True)
    surface_ha = Column(Float, default=1.0)
    irrigation = Column(String, nullable=True)
    soil_type = Column(String, nullable=True)
    main_crop = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# 3. Table des Sessions (Mémoire de la conversation)
class ConversationSession(Base):
    __tablename__ = "conversation_sessions"
    phone = Column(String, primary_key=True)
    history_json = Column(Text, default="[]")
    last_active = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

def _migrate():
    """Ajoute les colonnes manquantes si la DB existe déjà."""
    inspector = inspect(engine)
    columns = [c['name'] for c in inspector.get_columns('farmer_profiles')]
    
    with engine.connect() as conn:
        if "latitude" not in columns:
            from sqlalchemy import text
            conn.execute(text("ALTER TABLE farmer_profiles ADD COLUMN latitude REAL"))
        if "longitude" not in columns:
            from sqlalchemy import text
            conn.execute(text("ALTER TABLE farmer_profiles ADD COLUMN longitude REAL"))
        conn.commit()

def init_db():
    Base.metadata.create_all(bind=engine)
    try:
        _migrate()
    except Exception as e:
        print(f"Migration skip: {e}")
    print("✅ Base de données FELLAH.AI prête !")

if __name__ == "__main__":
    init_db()