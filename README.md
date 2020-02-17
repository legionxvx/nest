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

### Prerequisites

- Python 3.7 or newer
- Pipenv

```
$ pipenv install
```

### Installation

- To simply check out a working development environment; git checkout this 
repository and install the requirements
```
$ git clone git@git.harrisonconsoles.com:marketing/nest.git
$ cd nest
$ pipenv install
```

- To install this into a project as a submodule
```
$ cd your/git/project/
$ git submodule add git@git.harrisonconsoles.com:marketing/nest.git
```

## Running the tests

1. Set up a working development environment per the 
[Installation](#Installation) section
2. Run the following commands
```
$ pipenv install --dev
$ pipenv run pytest tests
```

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, 
see the [tags section](https://git.harrisonconsoles.com/marketing/nest/-/tags). 