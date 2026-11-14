from app import accounts, boards
from app.models import Edition, Plan
from tests.factories import PASSWORD


def make_admin(name="Acme", email="beheer@acme.nl", plan=Plan.UNLIMITED):
    accounts.request_admin_account(email=email, password=PASSWORD, organisation_name=name)
    return accounts.approve_admin(email, plan)


def make_member(admin, email="lid@acme.nl", team="Team A"):
    return accounts.add_member(admin=admin, email=email, password=PASSWORD, team_name=team)


def make_board(admin, team="Team A", name="Project", edition=Edition.TEAM):
    return boards.create_board(admin=admin, team_name=team, board_name=name, edition=edition)


def log_in(client, email, password=PASSWORD):
    return client.post("/login", data={"email": email, "password": password})
