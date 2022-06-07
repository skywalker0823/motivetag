
from data.data import Member
Member.sign_up




def test_new_user():
    """
    GIVEN a User model
    WHEN a new User is created
    THEN check the email, hashed_password, and role fields are defined correctly
    """
    user = Member.sign_up("123", "123","123@123.com","1988-09-12","2022-01-01")
    assert user.account == "123"
    assert user.email == '123@123.COM'
    assert user.hashed_password != '123'
