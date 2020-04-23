from datetime import date, timedelta

import app
from models import User


date = date.today()
previous_date = date - timedelta(days=7)

users = User.query.filter_by(is_active=True).filter(User.last_post_date == previous_date)

for user in users:
    user.post_track_status(allow_check=False)
