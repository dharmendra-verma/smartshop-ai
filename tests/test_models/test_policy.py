"""Tests for Policy model."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Policy


def test_policy_creation(db_session):
    """Test creating a policy with all fields."""
    policy = Policy(
        policy_type="returns",
        description="Laptop Return Policy",
        conditions="Laptop must be in unopened condition|All accessories included",
        timeframe=14,
    )
    db_session.add(policy)
    db_session.commit()

    assert policy.policy_id is not None
    assert policy.policy_type == "returns"
    assert policy.timeframe == 14


def test_policy_type_required(db_session):
    """Test that policy_type is required."""
    policy = Policy(description="D", conditions="C", timeframe=0)
    db_session.add(policy)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_policy_description_required(db_session):
    """Test that description is required."""
    policy = Policy(policy_type="test", conditions="C", timeframe=0)
    db_session.add(policy)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_policy_conditions_required(db_session):
    """Test that conditions is required."""
    policy = Policy(policy_type="test", description="D", timeframe=0)
    db_session.add(policy)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_policy_timeframe_default(db_session):
    """Test that timeframe defaults to 0."""
    policy = Policy(policy_type="test", description="D", conditions="C")
    db_session.add(policy)
    db_session.commit()
    assert policy.timeframe == 0


def test_policy_to_dict(sample_policy):
    """Test policy to_dict method."""
    policy_dict = sample_policy.to_dict()

    assert policy_dict["policy_type"] == "shipping"
    assert policy_dict["description"] == "Standard Shipping Policy"
    assert "|" in policy_dict["conditions"]
    assert policy_dict["timeframe"] == 5
    assert "policy_id" in policy_dict


def test_policy_repr(sample_policy):
    """Test policy string representation."""
    repr_str = repr(sample_policy)
    assert "Policy" in repr_str
    assert "shipping" in repr_str


def test_policy_query_by_type(db_session):
    """Test querying policies by policy_type."""
    types = ["shipping", "returns", "warranty", "shipping"]
    for i, pt in enumerate(types):
        db_session.add(Policy(policy_type=pt, description=f"D{i}", conditions=f"C{i}", timeframe=i * 10))
    db_session.commit()

    shipping = db_session.query(Policy).filter(Policy.policy_type == "shipping").all()
    assert len(shipping) == 2

    returns = db_session.query(Policy).filter(Policy.policy_type == "returns").all()
    assert len(returns) == 1


def test_policy_timeframe_handling(db_session):
    """Test timeframe is stored and retrieved correctly."""
    policy = Policy(policy_type="warranty", description="Extended Warranty", conditions="Covers defects", timeframe=365)
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)

    assert policy.timeframe == 365
    assert policy.to_dict()["timeframe"] == 365
