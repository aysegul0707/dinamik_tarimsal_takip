from app import db
from app.models.base import BaseModel

class AnalysisResult(BaseModel):
    __tablename__ = 'analysis_results'

    field_id = db.Column(db.Integer, db.ForeignKey('fields.id'), nullable=False)
    analysis_date = db.Column(db.Date, nullable=False)
    
    # Veriler
    ndvi_mean = db.Column(db.Float)
    ndmi_mean = db.Column(db.Float)
    msi_mean = db.Column(db.Float)
    
    # Risk
    risk_score = db.Column(db.Integer)
    risk_level = db.Column(db.String(20))
    alert_message = db.Column(db.Text)

class FieldModel(BaseModel):
    __tablename__ = 'field_models'

    field_id = db.Column(db.Integer, db.ForeignKey('fields.id'), nullable=False)
    model_path = db.Column(db.String(255))
    scaler_path = db.Column(db.String(255))
    is_ready = db.Column(db.Boolean, default=False)