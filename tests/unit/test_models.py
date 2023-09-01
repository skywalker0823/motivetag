#資料庫test

from data.data import Member

def test_get_user():
    """
    GIVEN a User account
    WHEN a User try to get data with account
    THEN check should return user data account include
    """
    user = Member.get_member("guest")
    assert user["account"] == "guest"

def test_new_user():
    """
    GIVEN a User model
    WHEN a User is created before
    THEN check should return Already registed
    """
    user = Member.sign_up("guest", "guest","guest@mail.com","1988-09-12","NULL")
    assert user == "Already registed"

