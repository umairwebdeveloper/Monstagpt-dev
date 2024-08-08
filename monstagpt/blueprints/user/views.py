import datetime
import pytz
import pycountry
from flask import Blueprint
from flask import flash
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask_httpauth import HTTPBasicAuth
from flask_login import current_user
from flask_login import login_required
from flask_login import login_user
from flask_login import logout_user
from flask import current_app
import ast
import pandas as pd

from lib.custom_logging_handler import send_slack_message
from lib.security import safe_next_url
from monstagpt.blueprints.user.decorators import anonymous_required
from monstagpt.blueprints.user.decorators import confirmed_required
from monstagpt.blueprints.user.forms import BeginPasswordResetForm
from monstagpt.blueprints.user.forms import ConfirmEmailForm
from monstagpt.blueprints.user.forms import LoginForm
from monstagpt.blueprints.user.forms import PasswordResetForm
from monstagpt.blueprints.user.forms import SignupForm
from monstagpt.blueprints.user.forms import UpdateCredentialsForm
from monstagpt.blueprints.user.forms import UpdateLocaleForm
from monstagpt.blueprints.user.forms import WelcomeForm
from monstagpt.blueprints.user.models import User
from monstagpt.blueprints.stripe_payments.models import ProductCatalog
from monstagpt.blueprints.admin.models import Settings
from monstagpt.blueprints.api.forms import DeleteKeyForm
from monstagpt.extensions import db

user = Blueprint("user", __name__, template_folder="templates")

auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    users_str = current_app.config["BASIC_AUTH_CREDS"]
    users = ast.literal_eval(users_str)
    if username in users and users[username] == password:
        return username
    
@user.before_request
# @auth.login_required
def before_request():
    """ Protect all of the gpt endpoints. """
    pass    

@user.route("/login", methods=["GET", "POST"])
@anonymous_required()
def login():
    form = LoginForm(next=request.args.get("next"))

    if form.validate_on_submit():
        form.identity.data = form.identity.data.lower()
        identity = form.identity.data.lower()
        # u = User.find_by_identity(request.form.get("identity"))
        u = User.find_by_identity(identity)

        if u and u.authenticated(password=request.form.get("password")):
            # As you can see remember me is always enabled, this was a design
            # decision I made because more often than not users want this
            # enabled. This allows for a less complicated login form.
            #
            # If however you want them to be able to select whether or not they
            # should remain logged in then perform the following 3 steps:
            # 1) Replace 'True' below with: request.form.get('remember', False)
            # 2) Uncomment the 'remember' field in user/forms.py#LoginForm
            # 3) Add a checkbox to the login form with the id/name 'remember'
            if login_user(u, remember=True):
                u.update_activity_tracking(request.remote_addr)

                # Handle optionally redirecting to the next URL safely.
                next_url = request.form.get("next")
                if next_url:
                    return redirect(safe_next_url(next_url))

                return redirect(url_for("user.dashboard"))
        else:
            flash("Identity or password is incorrect.", "error")

    return render_template("user/login.html", form=form)


@user.get("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("user.login"))


@user.route("/account/begin_password_reset", methods=["GET", "POST"])
@anonymous_required()
def begin_password_reset():
    form = BeginPasswordResetForm()

    if form.validate_on_submit():
        form.identity.data = form.identity.data.lower()
        u = User.initialize_password_reset(request.form.get("identity"))

        flash("An email has been sent to {0}.".format(u.email), "success")
        return redirect(url_for("user.login"))

    return render_template("user/begin_password_reset.html", form=form)


@user.route("/account/password_reset", methods=["GET", "POST"])
@anonymous_required()
def password_reset():
    form = PasswordResetForm(reset_token=request.args.get("reset_token"))

    if form.validate_on_submit():
        u = User.find_by_token(request.form.get("reset_token"))

        if u is None:
            flash(
                "Your reset token has expired or was tampered with.", "error"
            )
            return redirect(url_for("user.begin_password_reset"))

        form.populate_obj(u)
        u.password = User.encrypt_password(request.form.get("password"))
        u.save()

        if login_user(u):
            flash("Your password has been reset.", "success")
            return redirect(url_for("user.settings"))

    return render_template("user/password_reset.html", form=form)


@user.route("/signup", methods=["GET", "POST"])
@anonymous_required()
def signup():
    # setting = Settings.query.get(1)

    class Setting:
        def __init__(self):
            self.allow_signup = True
    
    slack_general_webhook_url = current_app.config.get("SLACK_GENERAL_WEBHOOK_URL")
    form = SignupForm()

    setting = Setting()

    if form.validate_on_submit():
        if not setting.allow_signup:

            flash('signups are currently disabled, please come back later','info')
            return render_template("user/signup.html", form=form)

        form.email.data = form.email.data.lower()
        u = User()

        form.populate_obj(u)
        u.password = User.encrypt_password(request.form.get("password"))
        u.save()

        if login_user(u):
            flash("Awesome, thanks for signing up!", "success")
            slack_message = f"""New user signed up: *{current_user.email}*\n"""
            send_slack_message(slack_general_webhook_url, slack_message)
            User.initialize_confirmation_email(u.email)
            return redirect(url_for("user.begin_email_confirmation"))

    return render_template("user/signup.html", form=form)

@user.route('/account/confirm_email', methods=['GET','POST'])
@login_required
def confirm_email():
    confirmation_token=request.args.get("confirmation_token")
    
    u = User.find_by_token(confirmation_token)

    if u is None:
            flash('Your confirmation token has expired or was tampered with.',
                'error')
            return redirect(url_for('user.begin_email_confirmation'))

    if login_user(u):
        u.account_is_confirmed = True
        u.account_confirmed_on = datetime.datetime.now(pytz.utc)
        u.save()
        flash(f'Your email has been confirmed, {u.email}', 'success')
        return redirect(url_for('user.settings'))
    
    return redirect(url_for('user.begin_email_confirmation'))


@user.route('/account/begin_email_confirmation', methods=['GET', 'POST'])
@login_required
def begin_email_confirmation():
    form = ConfirmEmailForm()
    if form.validate_on_submit():
        email = current_user.email
        User.initialize_confirmation_email(email)
        flash('An email has been sent to {0}.'.format(email), 'success')
        return redirect(url_for('user.begin_email_confirmation'))
    return render_template('user/begin_email_confirmation.html', form=form)

@user.route("/welcome", methods=["GET", "POST"])
@login_required
@confirmed_required
def welcome():
    if current_user.username:
        flash("You already picked a username.", "warning")
        return redirect(url_for("user.settings"))

    form = WelcomeForm()

    if form.validate_on_submit():
        current_user.username = request.form.get("username")
        current_user.save()

        flash("Sign up is complete, enjoy our services.", "success")
        return redirect(url_for("user.settings"))

    return render_template("user/welcome.html", form=form)

@user.get("/dashboard")
@login_required
@confirmed_required
def dashboard():
    return render_template("user/dashboard.html")

@user.get("/dashboard/dropdowns")
@login_required
@confirmed_required
def get_all_data():

    country_codes = [
            "AO", "AI", "AL", "AE", "AR", "AM", "AG", "AU", "AT", "AZ", "BE", "BJ", "BF", 
            "BG", "BH", "BS", "BY", "BZ", "BM", "BO", "BR", "BB", "BN", "BT", "BW", "CA", 
            "CH", "CL", "CN", "CG", "CO", "CV", "CR", "KY", "CY", "CZ", "DE", "DM", "DK", 
            "DO", "DZ", "EC", "EG", "ES", "EE", "FI", "FJ", "FR", "FM", "GB", "GH", "GM", 
            "GW", "GR", "GD", "GT", "GY", "HK", "HN", "HR", "HU", "ID", "IN", "IE", "IS", 
            "IL", "IT", "JM", "JO", "JP", "KZ", "KE", "KG", "KH", "KN", "KR", "KW", "LA", 
            "LB", "LR", "LC", "LK", "LT", "LU", "LV", "MO", "MD", "MG", "MX", "MK", "ML", 
            "MT", "MN", "MZ", "MR", "MS", "MU", "MW", "MY", "NA", "NE", "NG", "NI", "NL", 
            "NO", "NP", "NZ", "OM", "PK", "PA", "PE", "PH", "PW", "PG", "PL", "PT", "PY", 
            "QA", "RO", "RU", "SA", "SN", "SG", "SB", "SL", "SV", "ST", "SR", "SK", "SI", 
            "SE", "SZ", "SC", "TC", "TD", "TH", "TJ", "TM", "TT", "TN", "TR", "TW", "TZ", 
            "UG", "UA", "UY", "US", "UZ", "VC", "VE", "VG", "VN", "YE", "ZA", "ZW"
        ]
    countries = []
    for code in country_codes:
        country = pycountry.countries.get(alpha_2=code)
        if country:
            countries.append({"name": country.name, "value": country.alpha_2})

    # Sort countries by name
    countries = sorted(countries, key=lambda x: x['name'])

    data = {
        "platforms": [
            {"name": "Google Play", "value": "android"},
            {"name": "Itunes App Store", "value": "itunes"}
        ],
        "countries": countries,
        "categories": [
            {"name": "Lifestyle", "value": "LIFESTYLE"},
            {"name": "Educational games", "value": "GAME_EDUCATIONAL"},
            {"name": "Puzzle games", "value": "GAME_PUZZLE"},
            {"name": "Food and drink", "value": "FOOD_AND_DRINK"},
            {"name": "Trivia games", "value": "GAME_TRIVIA"},
            {"name": "Board games", "value": "GAME_BOARD"},
            {"name": "Travel and local", "value": "TRAVEL_AND_LOCAL"},
            {"name": "Health and fitness", "value": "HEALTH_AND_FITNESS"},
            {"name": "Comics", "value": "COMICS"},
            {"name": "Arcage games", "value": "GAME_ARCADE"},
            {"name": "Casual games", "value": "GAME_CASUAL"},
            {"name": "Auto and vehicles", "value": "AUTO_AND_VEHICLES"},
            {"name": "Education", "value": "EDUCATION"},
            {"name": "Word games", "value": "GAME_WORD"},
            {"name": "Books and reference", "value": "BOOKS_AND_REFERENCE"},
            {"name": "Events", "value": "EVENTS"},
            {"name": "Music and audio", "value": "MUSIC_AND_AUDIO"},
            {"name": "Strategy games", "value": "GAME_STRATEGY"},
            {"name": "Role playing games", "value": "GAME_ROLE_PLAYING"},
            {"name": "Parenting", "value": "PARENTING"},
            {"name": "Photography", "value": "PHOTOGRAPHY"},
            {"name": "Productivity", "value": "PRODUCTIVITY"},
            {"name": "Android wear", "value": "ANDROID_WEAR"},
            {"name": "Business", "value": "BUSINESS"},
            {"name": "Weather", "value": "WEATHER"},
            {"name": "Communication", "value": "COMMUNICATION"},
            {"name": "House and home", "value": "HOUSE_AND_HOME"},
            {"name": "Personalization", "value": "PERSONALIZATION"},
            {"name": "Adventure games", "value": "GAME_ADVENTURE"},
            {"name": "Shopping", "value": "SHOPPING"},
            {"name": "Sports games", "value": "GAME_SPORTS"},
            {"name": "Finance", "value": "FINANCE"},
            {"name": "Sports", "value": "SPORTS"},
            {"name": "Art and design", "value": "ART_AND_DESIGN"},
            {"name": "Social", "value": "SOCIAL"},
            {"name": "Action games", "value": "GAME_ACTION"},
            {"name": "Entertainment", "value": "ENTERTAINMENT"},
            {"name": "Racing games", "value": "GAME_RACING"},
            {"name": "Video players", "value": "VIDEO_PLAYERS"},
            {"name": "Music games", "value": "GAME_MUSIC"},
            {"name": "Card games", "value": "GAME_CARD"},
            {"name": "News and magaines", "value": "NEWS_AND_MAGAZINES"},
            {"name": "Beauty", "value": "BEAUTY"},
            {"name": "Simulation games", "value": "GAME_SIMULATION"},
            {"name": "Maps and navigation", "value": "MAPS_AND_NAVIGATION"},
            ],
        "dates": [ 
            {"name": "Jun 10, 2024", "value": "2024-05-25"},
            {"name": "Jul 10, 2024", "value": "2024-05-24"}
        ]
    }
    data['categories'] = sorted(data['categories'], key=lambda x: x['name'])
    return jsonify(data)

@user.route('/dashboard/get-apps-data', methods=['POST'])
def get_apps_data():
    data = request.get_json()
    print('***DATA****')
    print(data)
    platform = data.get('platform')
    country = data.get('country')
    category = data.get('category')
    date = data.get('date')

    category_free = 'apps_topfree-' + category
    category_paid = 'apps_toppaid-' + category
    category_grossing = 'apps_topgrossing-' + category

    # Read the dataframe
    rank_data = 'monstagpt/blueprints/user/ranks-data-29-07-2024.json'
    df = pd.read_json(rank_data, lines=True)
    df['timestamp'] = df['timestamp'].astype(str)

    # Update the 'price' column to 'Free' or 'Paid'
    df['price'] = df['price'].apply(lambda x: 'Free' if x.lower() == 'free' else 'Paid')

    # Filter the DataFrame for the specified conditions
    filtered_free_df = df[(df['rank_list'] == category_free) & 
                          (df['country'] == country) & 
                          (df['price'] == 'Free') & 
                          (df['timestamp'].str.contains(date))]
    
    filtered_paid_df = df[(df['rank_list'] == category_paid) & 
                        (df['country'] == country) & 
                        (df['price'] == 'Free') & 
                        (df['timestamp'].str.contains(date))]
    
    filtered_grossing_df = df[(df['rank_list'] == category_grossing) & 
                        (df['country'] == country) & 
                        (df['price'] == 'Free') & 
                        (df['timestamp'].str.contains(date))]
    
    # Further filter the DataFrame to include only the rows with the 10 lowest rank scores
    lowest_free_df = filtered_free_df.nsmallest(10, 'rank')
    lowest_paid_df = filtered_paid_df.nsmallest(10, 'rank')
    lowest_grossing_df = filtered_grossing_df.nsmallest(10, 'rank')

    # A hack to show dummy paid data for word games
    if category == 'GAME_WORD':
        lowest_paid_df = filtered_free_df.iloc[10:20]

    # Assume you fetch data based on the filters
    free_apps = lowest_free_df.apply(lambda row: {'name': row['app_name'], 'publisher': row['publisher_name'],'icon':row['icon_url'],'rating':row['avg_rating']}, axis=1).tolist()
    paid_apps = lowest_paid_df.apply(lambda row: {'name': row['app_name'], 'publisher': row['publisher_name'],'icon':row['icon_url'],'rating':row['avg_rating']}, axis=1).tolist()
    grossing_apps = lowest_grossing_df.apply(lambda row: {'name': row['app_name'], 'publisher': row['publisher_name'],'icon':row['icon_url'],'rating':row['avg_rating']}, axis=1).tolist()

    return jsonify({
        'freeApps': free_apps,
        'paidApps': paid_apps,
        'grossingApps': grossing_apps
    })

@user.get("/settings")
@login_required
@confirmed_required
def settings():
    # Check to see if the user has a subscription. If it has expired, set the subscription coins to zero.
    user_plan = 'Free'
    if current_user.subscription:
        time_now = datetime.datetime.now(pytz.utc).timestamp()
        print(f'time_now {int(time_now)}')
        if current_user.subscription.subscription_ends < time_now:
            current_user.subscribed_coins = 0
            current_user.subscription.status = 'expired'
            current_user.subscription.plan = 'Free'
            db.session.commit()
            flash('Your subscription has expired','error')
        user_plan = current_user.subscription.plan
    rate_limit = ProductCatalog.query.filter_by(tier=user_plan).first().rate_limit_seconds
    delete_forms = [DeleteKeyForm(api_key=key.api_key) if current_user.api else None for key in current_user.api]
    return render_template("user/settings.html",delete_forms=delete_forms,user_plan=user_plan,rate_limit=rate_limit)


@user.route("/settings/update_credentials", methods=["GET", "POST"])
@login_required
@confirmed_required
def update_credentials():
    form = UpdateCredentialsForm(obj=current_user)

    if form.validate_on_submit():
        new_password = request.form.get("password", "")
        current_user.email = request.form.get("email")

        if new_password:
            current_user.password = User.encrypt_password(new_password)

        current_user.save()

        flash("Your sign in settings have been updated.", "success")
        return redirect(url_for("user.settings"))

    return render_template("user/update_credentials.html", form=form)


@user.route("/settings/update_locale", methods=["GET", "POST"])
@login_required
@confirmed_required
def update_locale():
    form = UpdateLocaleForm(locale=current_user.locale)

    if form.validate_on_submit():
        form.populate_obj(current_user)
        current_user.save()

        flash("Your locale settings have been updated.", "success")
        return redirect(url_for("user.settings"))

    return render_template("user/update_locale.html", form=form)
