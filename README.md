# Nest
Nest is a module providing a common interface for projects like 
[Augur]() and [Sentinel](https://git.harrisonconsoles.com/marketing/sentinel).

Currently it supports the following features:

- Interfaces for the following APIs
  - FastSpring
  - Mailchimp
- Redis locking
- Product definitions
- PostgreSQL database engine and model
- Database migration

### Prerequisites

- Python 3.7 or newer
- Pipenv or Pip

```
$ pipenv install
or
$ pip install -r requirements.txt
```

### Installation

- To simply check out a working development environment; git checkout this 
repository and install the requirements
```
$ git clone git@git.harrisonconsoles.com:marketing/nest.git
$ cd nest
$ pipenv install
```

- To install using pipenv (subject to change as I figure it out)
```
$ pipenv install git+ssh://git@git.harrisonconsoles.com/marketing/nest.git#egg=nest
```

## Configuration

TBA

## Running the tests

1. Set up a working development environment per the 
[Installation](#Installation) section
2. (Optional) Create a pytest.ini to provide API credentials and other 
environment variables.
```
[pytest]
env =
    D:MAILCHIMP_AUTH_USER=John Doe
    D:MAILCHIMP_AUTH_TOKEN=foo
    D:DEFAULT_MAILCHIMP_LIST=bar

    D:FS_AUTH_USER=baz
    D:FS_AUTH_PASS=biz

```
3. (Optional) Install postgres-12 and redis-server packaged from your 
repository to test RedisEngine and PostgreSQLEngine transactions.
4. Run the following commands
```
$ pipenv install --dev
$ pipenv run pytest tests
```

## Building docs

1. Set up a working development environment per the 
[Installation](#Installation) section
2. Run the following commands
```
$ pipenv install --dev
$ cd docs
$ pipenv run make html
```

## Database Migration

Migration revisions need to be generated after every major (and most minor) 
change. This includes the any of the following

- A new model definition
- Column name/constraint changes
- New relationships

Migration versioning is handled by Alembic. Alembic is configured to generate 
automated revisions using.
```
$ pipenv run alembic revision --autogenerate -m "Description"
```


- To upgrade your database
```
$ pipenv run alembic upgrade head
or
$ pipenv run alembic upgrade $REVISION
```
- To downgrade your database
```
$ pipenv run alembic downgrade $REVISION
```

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, 
see the [tags section](https://git.harrisonconsoles.com/marketing/nest/-/tags). 