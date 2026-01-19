from app import db
from app.models.base import BaseModel

class Field(BaseModel):
    __tablename__ = 'fields'

    name = db.Column(db.String(100), nullable=False)
    location_name = db.Column(db.String(100))
    coordinates = db.Column(db.Text, nullable=False) # JSON string
    crop_type = db.Column(db.String(50))
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # İlişkiler
    analyses = db.relationship('AnalysisResult', backref='field', lazy='dynamic', cascade="all, delete-orphan")
    ml_model = db.relationship('FieldModel', backref='field', uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Field {self.name}>'