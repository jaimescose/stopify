from datetime import datetime, timedelta

import app
from models import User


since = datetime.now() - timedelta(days=7)

users = User.query.filter_by(is_active=True).filter(User.last_post_date < since)

for user in users:
    user.post_track_status(allow_check=False)

print(f'Statuses posted for {users.count()} users')
