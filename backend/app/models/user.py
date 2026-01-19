from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models.base import BaseModel

class User(BaseModel):
    __tablename__ = 'users'

    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(128))
    
    # 'free', 'premium', 'admin'
    subscription_type = db.Column(db.String(20), default='free')
    
    # İlişkiler
    fields = db.relationship('Field', backref='owner', lazy='dynamic', cascade="all, delete-orphan")

    @property
    def password(self):
        raise AttributeError('Şifre okunamaz!')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'