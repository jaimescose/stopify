from flask.cli import FlaskGroup

from app import app, db
from flask import session

cli = FlaskGroup(app)

@cli.command("create_db")
def create_db():
    db.drop_all()
    db.create_all()
    db.session.commit()


@cli.comman('clear_sessions')
def clear_sessions():
    session.clear()

if __name__ == "__main__":
    cli()
