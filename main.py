import asyncio

from schemas import RegisterUserData
from tools import get_wd, get_number, register_number, save_number

if __name__ == "__main__":
    while True:
        number = get_number()
        wd = get_wd(no_reset=False)
        number = register_number(wd, number, RegisterUserData(first_name="Artem"))
        # wd.close()
        if number:
            asyncio.run(save_number(wd, number))
            break
