from flask import jsonify
from datetime import datetime
import json
from monstagpt.blueprints.ignite.decorators import parameters_required
from monstagpt.app import create_celery_app

celery = create_celery_app()

from sqlalchemy import create_engine, Column, String, select, Float, Date, text, or_
from sqlalchemy.orm import declarative_base, sessionmaker

# Define the base class for ORM
Base = declarative_base()

# Define your database connection string
DATABASE_URL = 'postgresql://readonly_user:4d4d72f86610443992a192eba5034382@gpt-postgtes.csmxqsfrip4l.us-east-1.rds.amazonaws.com:5432/gpt_data'


# Create the database engine
engine = create_engine(DATABASE_URL)

# Define sessionmaker
Session = sessionmaker(bind=engine)

# Function to get the name by id and platform
@celery.task(queue='queue2')
def get_name_by_id_and_platform(app_id, app_platform):
    # Create a new session
    session = Session()
    query = text("""select name from app_names
            where id = :app_id
            and platform = :app_platform;""")

    result_proxy = session.execute(query, {'app_id': app_id, 'app_platform': app_platform})
    results = result_proxy.fetchall()
    print('*ALL REULTS**')
    print(results)  

    results_list = [
        {
            'name': row[0],
        }
        for row in results
    ]
    results_dict = {"data": results_list}
    
    return json.dumps(results_dict)

# Function to get the name by id and platform
@celery.task(queue='queue2')
def get_id_by_name_and_platform(app_name, app_platform):
    # Create a new session
    session = Session()
    query = text("""select id from app_names
            where name = :app_name
            and platform = :app_platform;""")
    print('**APP NAME**')
    print(app_name)
    result_proxy = session.execute(query, {'app_name': app_name, 'app_platform': app_platform})
    results = result_proxy.fetchall()
    print('*ALL REULTS**')
    print(results)  

    results_list = [
        {
            'id': row[0],
        }
        for row in results
    ]
    results_dict = {"data": results_list}
    
    return json.dumps(results_dict)

@celery.task(queue='queue2')
def get_data_safety_data(app_id, app_platform):
    # Create a new session
    session = Session()

    query = text("""select * from data_safety
                where id = :app_id
                and platform = :app_platform;""")

    result_proxy = session.execute(query, {'app_id': app_id, 'app_platform': app_platform})
    results = result_proxy.fetchall()
    # Explicitly construct the list of dictionaries

    results_list = [
        {
            'id': row[1],
            'security_practices': row[0],
            'platform': row[2],
            'data_shared': row[3],
            'data_collected': row[4]
        }
        for row in results
    ]
    results_dict = {"data": results_list}
    
    return json.dumps(results_dict)

@celery.task(queue='queue2')
def get_details_data(app_id, app_platform):
    # Create a new session
    session = Session()

    query = text("""select * from details
                where id = :app_id
                and platform = :app_platform;""")

    result_proxy = session.execute(query, {'app_id': app_id, 'app_platform': app_platform})
    results = result_proxy.fetchall()
    # Explicitly construct the list of dictionaries

    results_list = [
        {
            'id': row[0],
            'content_rating': row[1],
            'price': row[2],
            'publisher_name': row[3],
            'all_rating': row[4],
            'genre': row[5],
            'icon_url': row[6],
            'version': row[7],
            'publisher_url': row[8],
            'screenshot_url': row[9],
            'status': row[10],
            'description': row[11],
            'price_value': row[12],
            'status_date': row[13],
            'whats_new': row[14],
            'release_date': row[15],
            'all_rating_count': row[16],
            'platform': row[17],
        }
        for row in results
    ]
    results_dict = {"data": results_list}
    
    return json.dumps(results_dict)

@celery.task(queue='queue2')
def get_top_estimates(data_type, platform, start_date, end_date, limit):
    # Create a new session
    session = Session()

    # Convert start_date and end_date to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()


    query = text(f"""
        SELECT id, SUM({data_type})
        FROM {data_type}
        WHERE platform = :platform
        AND date >= :start_date
        AND date <= :end_date
        GROUP BY id
        ORDER BY SUM({data_type}) DESC
        LIMIT :limit;
    """)

    result_proxy = session.execute(query, {
        'platform': platform,
        'start_date': start_date,
        'end_date': end_date,
        'limit': limit
    })
    results = result_proxy.fetchall()

    results_list = [
        {
            'id': row[0],
            'sum': row[1]
        }
        for row in results
    ]
    results_dict = {"data": results_list}

    return json.dumps(results_dict)

@celery.task(queue='queue2')
def get_downloads_data(app_id, app_platform, start_date, end_date):
    # Create a new session
    session = Session()

    # Convert start_date and end_date to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    query = text("""select * from downloads
                where id = :app_id
                and platform = :app_platform
                and date >= :start_date
                and date <= :end_date;""")

    result_proxy = session.execute(query, {'app_id': app_id, 'app_platform': app_platform, 'start_date': start_date, 'end_date': end_date})
    results = result_proxy.fetchall()
    # Explicitly construct the list of dictionaries

    results_list = [
        {
            'id': row[1],
            'platform': row[0],
            'downloads_country': row[2],
            'downloads': row[3],
            'date': row[4].isoformat() if row[4] else None  # Convert date to string
        }
        for row in results
    ]
    results_dict = {"data": results_list}
    
    return json.dumps(results_dict)

@celery.task(queue='queue2')
def get_rankings_data(app_id, app_platform, start_date, end_date):
    # Create a new session
    session = Session()

    # Convert start_date and end_date to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    query = text("""select * from rankings
                where id = :app_id
                and platform = :app_platform
                and date >= :start_date
                and date <= :end_date;""")

    result_proxy = session.execute(query, {'app_id': app_id, 'app_platform': app_platform, 'start_date': start_date, 'end_date': end_date})
    results = result_proxy.fetchall()
    # Explicitly construct the list of dictionaries

    results_list = [
        {
            'id': row[3],
            'platform': row[9],
            'rank_list': row[0],
            'name': row[1],
            'date': row[2].isoformat(),
            'rank': row[4],
            'country': row[5],
            'publisher_name': row[6],
            'publisher_id': row[7],
            'price': row[8],
            
        }
        for row in results
    ]
    results_dict = {"data": results_list}
    
    return json.dumps(results_dict)

@celery.task(queue='queue2')
def get_revenue_data(app_id, app_platform, start_date, end_date):
    # Create a new session
    session = Session()

    # Convert start_date and end_date to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    query = text("""select * from revenue
                where id = :app_id
                and platform = :app_platform
                and date >= :start_date
                and date <= :end_date;""")

    result_proxy = session.execute(query, {'app_id': app_id, 'app_platform': app_platform, 'start_date': start_date, 'end_date': end_date})
    results = result_proxy.fetchall()
    # Explicitly construct the list of dictionaries

    results_list = [
        {
            'id': row[1],
            'platform': row[0],
            'revenue_country': row[2],
            'revenue': row[3],
            'date': row[4].isoformat() if row[4] else None  # Convert date to string
        }
        for row in results
    ]
    results_dict = {"data": results_list}
    
    return json.dumps(results_dict)

@celery.task(queue='queue2')
def get_reviews_data(app_id, app_platform, start_date, end_date):
    # Create a new session
    session = Session()

    # Convert start_date and end_date to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    query = text("""select * from reviews
                where id = :app_id
                and platform = :app_platform
                and date >= :start_date
                and date <= :end_date
                order by date DESC 
                limit 20;""")

    result_proxy = session.execute(query, {'app_id': app_id, 'app_platform': app_platform, 'start_date': start_date, 'end_date': end_date})
    results = result_proxy.fetchall()
    # Explicitly construct the list of dictionaries

    results_list = [
        {
            'id': row[2],
            'platform': row[5],
            'rating': row[0],
            'username': row[1],
            'review_text': row[3],
            'date': row[4].isoformat(),
        }
        for row in results
    ]
    results_dict = {"data": results_list}
    
    return json.dumps(results_dict)