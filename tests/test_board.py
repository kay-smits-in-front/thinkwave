import pytest
from sqlalchemy import select

from app import board
from app.extensions import db
from app.models import Action, Organisation, Phase, Project, ProjectAction


@pytest.mark.parametrize(
    ("impact", "sweetspot", "expected"),
    [(20, 20, 2.0), (26, 20, 1.2), (35, 20, 1.0), (45, 20, 0.8), (55, 20, 0.5), (90, 20, 0.2)],
)
def test_multiplier_steps_match_old_board(impact, sweetspot, expected):
    assert board.multiplier(impact, sweetspot) == expected


def make_project(total_weeks: int = 104) -> Project:
    org = db.session.scalar(select(Organisation)) or Organisation(name="Acme")
    db.session.add(org)
    db.session.flush()
    project = Project(name="Test", organisation_id=org.id, total_weeks=total_weeks)
    db.session.add(project)
    db.session.commit()
    return project


def action(name: str) -> Action:
    return db.session.scalar(select(Action).filter_by(name=name))


def test_seed_loads_all_actions_once(seeded):
    board.seed_actions()
    assert db.session.query(Action).count() == 36


def test_performing_adds_impact_and_time(seeded):
    project = make_project()
    talk = action("Talk to Customer")  # sweetspot 0: bij een lege fase het meest waard
    step = board.perform(project, talk)
    assert step.impact_percent == 10.0
    assert board.phase_impacts(project)[Phase.RESEARCH] == 10.0
    assert board.weeks_used(project) == 5
    assert board.uses_left(project, talk) == 2


def test_action_cannot_be_used_more_than_its_frequency(seeded):
    project = make_project()
    ecosystem = action("Ecosystem Mapping")  # maximaal 1 keer
    board.perform(project, ecosystem)
    with pytest.raises(ValueError):
        board.perform(project, ecosystem)


def test_timeline_full_blocks_steps_and_shows_ending(seeded):
    project = make_project(total_weeks=5)
    board.perform(project, action("Talk to Customer"))
    assert board.ending(project) is not None
    assert not board.can_perform(project, action("Testing"))


def test_intermission_feedback_after_first_quarter(seeded):
    project = make_project(total_weeks=20)
    assert board.intermission_feedback(project) is None
    board.perform(project, action("Brainstorming"))  # 5 van 20 weken: eerste kwart voorbij
    feedback = board.intermission_feedback(project)
    assert feedback.title == "Make sure you are aware of the facts a bit more!"  # research < 20%


def test_suggestions_prefer_highest_expected_impact(seeded):
    project = make_project()
    names = [a.name for a in board.suggest(project)]
    zero_sweetspot = {"Talk to Customer", "Kickstarter", "Business Plan"}
    assert set(names) == zero_sweetspot


def test_suggestions_use_ratings_from_other_projects_as_tiebreak(seeded):
    other = make_project()
    step = board.perform(other, action("Business Plan"))
    step.self_rating = 5
    db.session.commit()
    project = Project(name="Nieuw", organisation_id=other.organisation_id)
    db.session.add(project)
    db.session.commit()
    assert board.suggest(project, limit=1)[0].name == "Business Plan"


def test_rating_must_be_between_one_and_five(seeded):
    project = make_project()
    step = board.perform(project, action("Testing"))
    step.self_rating = 9
    with pytest.raises(Exception):
        db.session.commit()
    db.session.rollback()
    assert db.session.get(ProjectAction, step.id).self_rating is None


def test_duration_can_be_set_per_project(seeded):
    project = make_project()
    step = board.perform(project, action("Testing"), duration_weeks=3)
    assert step.duration_weeks == 3
    assert board.weeks_used(project) == 3


def test_organisation_copy_replaces_default_on_work_board_only(seeded):
    from app.models import Board

    work = make_project()
    original = action("Testing")
    copy = board.editable_copy(original, work.organisation_id)
    copy.name = "Gebruikerstest"
    db.session.commit()

    names = [a.name for a in board.catalog(work)]
    assert "Gebruikerstest" in names and "Testing" not in names
    assert len(names) == 36

    youth = Project(name="Klas", organisation_id=work.organisation_id, board=Board.YOUTH)
    db.session.add(youth)
    db.session.commit()
    assert "Testing" in [a.name for a in board.catalog(youth)]
    assert board.editable_copy(copy, work.organisation_id) is copy  # geen tweede kopie


def test_ratings_of_copies_count_for_the_default_task(seeded):
    project = make_project()
    copy = board.editable_copy(action("Business Plan"), project.organisation_id)
    db.session.commit()
    step = board.perform(project, copy)
    step.self_rating = 5
    db.session.commit()
    assert board.average_ratings()[action("Business Plan").id] == 5.0
