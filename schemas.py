from pydantic import BaseModel


class NumberGet(BaseModel):
    activation_id: str
    full_phone_number: str
    phone_number: str
    country_code: str


class RegisterUserData(BaseModel):
    first_name: str
