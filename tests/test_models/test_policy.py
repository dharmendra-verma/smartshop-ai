"""Tests for Policy model."""

import pytest
from datetime import date
from sqlalchemy.exc import IntegrityError

from app.models import Policy


def test_policy_creation(db_session):
    """Test creating a policy with all fields."""
    policy = Policy(
        category="returns",
        question="What is the return window?",
        answer="30 days from purchase.",
        effective_date=date(2026, 1, 1),
    )
    db_session.add(policy)
    db_session.commit()

    assert policy.policy_id is not None
    assert policy.category == "returns"
    assert policy.effective_date == date(2026, 1, 1)


def test_policy_category_required(db_session):
    """Test that category is required."""
    policy = Policy(question="Q", answer="A", effective_date=date(2026, 1, 1))
    db_session.add(policy)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_policy_question_required(db_session):
    """Test that question is required."""
    policy = Policy(category="test", answer="A", effective_date=date(2026, 1, 1))
    db_session.add(policy)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_policy_answer_required(db_session):
    """Test that answer is required."""
    policy = Policy(category="test", question="Q", effective_date=date(2026, 1, 1))
    db_session.add(policy)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_policy_effective_date_required(db_session):
    """Test that effective_date is required."""
    policy = Policy(category="test", question="Q", answer="A")
    db_session.add(policy)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_policy_to_dict(sample_policy):
    """Test policy to_dict method."""
    policy_dict = sample_policy.to_dict()

    assert policy_dict["category"] == "shipping"
    assert policy_dict["question"] == "What is the shipping time?"
    assert policy_dict["effective_date"] == "2026-01-01"
    assert "policy_id" in policy_dict


def test_policy_repr(sample_policy):
    """Test policy string representation."""
    repr_str = repr(sample_policy)
    assert "Policy" in repr_str
    assert "shipping" in repr_str


def test_policy_query_by_category(db_session):
    """Test querying policies by category."""
    categories = ["shipping", "returns", "privacy", "shipping"]
    for i, cat in enumerate(categories):
        db_session.add(Policy(category=cat, question=f"Q{i}", answer=f"A{i}", effective_date=date(2026, 1, 1)))
    db_session.commit()

    shipping = db_session.query(Policy).filter(Policy.category == "shipping").all()
    assert len(shipping) == 2

    returns = db_session.query(Policy).filter(Policy.category == "returns").all()
    assert len(returns) == 1


def test_policy_date_handling(db_session):
    """Test effective_date is stored and retrieved correctly."""
    policy = Policy(category="test", question="Q", answer="A", effective_date=date(2026, 6, 15))
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)

    assert policy.effective_date == date(2026, 6, 15)
    assert policy.to_dict()["effective_date"] == "2026-06-15"
