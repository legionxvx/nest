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

Nest looks for its configuration and credentials in the following order 
(first found is used):

1. Arguments passed into constructors at runtime
2. `config.yaml` or `config.yml` in its root directory
3. Environment variables with the same variable names as those found in 
`config.yaml`

Using `config.yaml` is usually most convenient.

## Running the tests

1. Set up a working development environment per the 
[Installation](#Installation) section
2. Run the following commands
```
$ pipenv install --dev
$ pipenv run pytest tests
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