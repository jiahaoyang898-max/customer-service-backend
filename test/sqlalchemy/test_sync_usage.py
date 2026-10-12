from models import Base, User
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

def main():
    engine = create_engine("sqlite:///mydb", echo=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        spongebob = User(
            name="Mr 张",
            fullname="张三"
        )

        sandy = User(
            name="sandy",
            fullname="Sandy Cheeks"
        )

        patrick = User(
            name="patrick",
            fullname="Patrick Star"
        )
        session.add_all([spongebob, sandy, patrick])
        session.commit()
        stmt = select(User).where(User.name.in_(["Mr 张", "sandy"]))
        for user in session.scalars(stmt):
            print(user)
        stmt = select(User).where(User.name == 'Mr 张')
        print(session.scalars(stmt).one())

if __name__ == '__main__':
    main()