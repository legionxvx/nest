from setuptools import setup

requirements = [
    "certifi>=2019.11.28",
    "chardet>=3.0.4",
    "colorlog>=4.1.0",
    "idna>=2.9",
    "psycopg2-binary>=2.8.4",
    "redis>=3.4.1",
    "redlock>=1.2.0",
    "requests>=2.23.0",
    "sqlalchemy>=1.3.13",
    "urllib3>=1.25.8",
]

setup(
    name="Nest",
    version="0.1",
    description="",
    author="Nikolaus Gullotta",
    packages=["nest"],
    install_requires=requirements,
)