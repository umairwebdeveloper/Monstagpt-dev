from sqlalchemy import func, extract
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz

from monstagpt.blueprints.billing.models.subscription import Subscription
from monstagpt.blueprints.user.models import User
from monstagpt.blueprints.user.models import db
from lib.util_sqlalchemy import ResourceMixin
from monstagpt.blueprints.gpt.models.gpt import Gpt

class Dashboard(object):
    @classmethod
    def group_and_count_users(cls):
        """
        Perform a group by/count on all users.

        :return: dict
        """
        return Dashboard._group_and_count(User, User.role)

    @classmethod
    def group_and_count_plans(cls):
        """
        Perform a group by/count on all subscriber types.

        :return: dict
        """
        return Dashboard._group_and_count(Subscription, Subscription.plan)

    @classmethod
    def group_and_count_coupons(cls):
        """
        Obtain coupon usage statistics across all subscribers.

        :return: tuple
        """
        not_null = (
            db.session.query(Subscription)
            .filter(Subscription.coupon.isnot(None))
            .count()
        )
        total = db.session.query(func.count(Subscription.id)).scalar()

        if total == 0:
            percent = 0
        else:
            percent = round((not_null / float(total)) * 100, 1)

        return not_null, total, percent

    @classmethod
    def _group_and_count(cls, model, field):
        """
        Group results for a specific model and field.

        :param model: Name of the model
        :type model: SQLAlchemy model
        :param field: Name of the field to group on
        :type field: SQLAlchemy field
        :return: dict
        """
        count = func.count(field)
        query = db.session.query(count, field).group_by(field).all()

        results = {"query": query, "total": model.query.count()}

        return results

    @classmethod
    def group_and_count_cost(cls):
        """
        Perform a group by/count on all gpt costs.

        :return: dict
        """

        monthly_costs = {}
        
        # Set timezone (replace 'UTC' with the timezone of your 'created_on' column if it's different)
        tz = pytz.timezone('UTC')

        # Calculate the first day of the month two months before the current date
        today = datetime.now().replace(tzinfo=tz)
        two_months_ago = today - relativedelta(months=2)
        first_day_two_months_ago = two_months_ago.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Execute the query to get total_cost grouped by month and year for the last two months
        results = (
            db.session.query(
                func.sum(Gpt.total_cost).label('total_cost'),
                extract('year', Gpt.created_on).label('year'),
                extract('month', Gpt.created_on).label('month')
            )
            .filter(Gpt.created_on >= first_day_two_months_ago)  # Filter to consider only the last two months
            .group_by(extract('year', Gpt.created_on), extract('month', Gpt.created_on))
            .all()
        )

        # Parse the results and populate the monthly_costs dictionary
        for result in results:
            year = int(result.year)  # Convert Decimal to int
            month = int(result.month)  # Convert Decimal to int
            total_cost = result.total_cost  # Handle the case where this is None
            
            # Format the month and year as "YYYY-MM"
            month_key = f"{year}-{month:02d}"
            monthly_costs[month_key] = round(float(total_cost),2) if total_cost else 0  # Convert to float and handle None case
        
        return monthly_costs


    @classmethod
    def get_user_costs_for_current_month(cls):
        today = datetime.now()
        current_month = today.month
        current_year = today.year
        
        # Assuming User model has a relationship with Gpt model named 'gpts'
        results = (
            db.session.query(User, func.sum(Gpt.total_cost).label('total_cost'))
            .join(Gpt)
            .filter(extract('month', Gpt.created_on) == current_month)
            .filter(extract('year', Gpt.created_on) == current_year)
            .group_by(User)
            .order_by(db.desc('total_cost'))
            .limit(5)  # Limit the results to the top 5 users
            .all()
        )
        
        user_costs = [{"user": user.email, "total_cost": round(float(total_cost or 0), 2)} for user, total_cost in results]
        return user_costs


class Settings(ResourceMixin, db.Model):
    __tablename__ = "settings"
    id = db.Column(db.Integer, primary_key=True)

    allow_signup = db.Column(db.Boolean(), nullable=True, server_default="1")

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Settings, self).__init__(**kwargs)

    def save_and_update_settings(self):
        """
        Commit the settings.

        :return: SQLAlchemy save result
        """
        self.save()
        return self.save()
    