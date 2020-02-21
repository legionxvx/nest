from setuptools import setup

install_requires = [
    "alembic>=1.4.0",
    "certifi>=2019.11.28",
    "chardet>=3.0.4",
    "colorlog>=4.1.0",
    "idna>=2.9",
    "mako>=1.1.1",
    "markupsafe>=1.1.1",
    "psycopg2-binary>=2.8.4",
    "python-dateutil>=2.8.1",
    "python-editor>=1.0.4",
    "redis>=3.4.1",
    "redlock>=1.2.0",
    "requests>=2.23.0",
    "six>=1.14.0",
    "sqlalchemy>=1.3.13",
    "urllib3>=1.25.8",
]

setup(
    name='Foo',
    version='0.1',
    description='',
    author='Foo Bar',
    author_email='test@testerson.com',
    packages=['nest'],
    install_requires=install_requires,
)