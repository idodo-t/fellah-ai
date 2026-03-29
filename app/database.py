from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

# On crée le fichier de base de données
SQLALCHEMY_DATABASE_URL = "sqlite:///./fellah_ai.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modèle pour stocker chaque diagnostic (IA Vision)
class DiagnosticRecord(Base):
    __tablename__ = "diagnostics"
    id = Column(Integer, primary_key=True, index=True)
    farmer_phone = Column(String)
    disease_detected = Column(String)
    confidence_score = Column(Float)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

# Création automatique des tables
def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Base de données initialisée avec SQLAlchemy !")

if __name__ == "__main__":
    init_db()