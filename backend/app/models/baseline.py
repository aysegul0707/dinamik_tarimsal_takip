from app import db
from app.models.base import BaseModel
import json

class Baseline(BaseModel):
    __tablename__ = 'baselines'

    field_id = db.Column(db.Integer, db.ForeignKey('fields.id'), nullable=False)
    week = db.Column(db.Integer, nullable=False)
    
    # İstatistiksel Veriler (Mean & Sigma)
    ndvi_mu = db.Column(db.Float, nullable=False)
    ndvi_sigma = db.Column(db.Float, nullable=False)
    
    ndmi_mu = db.Column(db.Float, nullable=False)
    ndmi_sigma = db.Column(db.Float, nullable=False)
    
    msi_mu = db.Column(db.Float, nullable=False)
    msi_sigma = db.Column(db.Float, nullable=False)
    
    sample_count = db.Column(db.Integer)
    years_used = db.Column(db.Text) # Hangi yılların verisi kullanıldı (JSON String)

    # Aynı tarla ve hafta için tekrar kayıt olamaz
    __table_args__ = (db.UniqueConstraint('field_id', 'week', name='unique_field_week'),)

    def __repr__(self):
        return f'<Baseline Field:{self.field_id} Week:{self.week}>'