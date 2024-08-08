import datetime
import pytz

from lib.util_sqlalchemy import ResourceMixin
from monstagpt.extensions import db

class ProductCatalog(ResourceMixin, db.Model):
    __tablename__ = "product_catalog"
    id = db.Column(db.Integer, primary_key=True)
    
    # Product details
    tier = db.Column(db.String(30), nullable=False, unique=True)
    rate_limit_seconds = db.Column(db.Integer, nullable=False)
    
    def __init__(self, **kwargs):
        super(ProductCatalog, self).__init__(**kwargs)
    
    @classmethod
    def update_tier(cls, tier, rate_limit_seconds):
        """
        Updates the rate_limit_seconds for a given tier.
        If the tier does not exist, it creates a new entry.
        
        Args:
            tier (str): The name of the tier.
            rate_limit_seconds (int): The new rate limit in seconds.
            
        Raises:
            ValueError: If the input parameters are invalid.
        """
        if not isinstance(tier, str) or not isinstance(rate_limit_seconds, int):
            raise ValueError("Invalid input parameters.")
        
        try:
            tier_entry = cls.query.filter_by(tier=tier).first()
            if tier_entry:
                tier_entry.rate_limit_seconds = rate_limit_seconds
            else:
                new_tier = cls(tier=tier, rate_limit_seconds=rate_limit_seconds)
                db.session.add(new_tier)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Log the error
            print(f"Error updating tier: {e}")
            raise