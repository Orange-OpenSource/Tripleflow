# Tripleflow

<p align="center">
  Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.
</p>

## Table of contents

- [Quick start](#quick-start)
- [Bugs and feature requests](#bugs-and-feature-requests)
- [Contributing](#contributing)
- [Versioning](#versioning)
- [Copyright and license](#copyright-and-license)

## Quick start

### System requirements

- Python 3.8 or higher. 
- Node / NPM 
- Docker
- Make

### Installation and launch with Python and Vue.js

1. Dependency installation

```bash
cd tripleflow-api && python3 -m pip install -r requirements.txt && uvicorn app.main:app
```

```bash
cd tripleflow-front && npm install && npm run dev
```

2. Launch app

```bash
cd tripleflow-api && uvicorn app.main:app
```

```bash
cd tripleflow-front && npm install && npm run dev
```

### Installation and launch with Docker

1. API 

```bash
cd tripleflow-api && make docker-build
```

```bash
cd tripleflow-api && make docker-run
```

2. Front

```bash
cd tripleflow-front && make docker-build
```

```bash
cd tripleflow-front && make docker-run
```


## Bugs and feature requests

Have a bug or a feature request? Please first read the [issue guidelines](https://github.com/Orange-OpenSource/tripleflow/blob/main/CONTRIBUTING.md#using-the-issue-tracker) and search for existing and closed issues. If your problem or idea is not addressed yet, [please open a new issue](https://github.com/Orange-OpenSource/tripleflow/issues/new/choose).

## Contributing

Please read through our [contributing guidelines](https://github.com/Orange-OpenSource/tripleflow/blob/main/CONTRIBUTING.md). Included are directions for opening issues, coding standards, and notes on development.

Please refer to the [quick start] for information on how to launch the application.

## Versioning

For transparency into our release cycle and in striving to maintain backward compatibility, Tripleflow is maintained under [the Semantic Versioning guidelines](https://semver.org/). Sometimes we screw up, but we adhere to those rules whenever possible.

See [the Releases section of our GitHub project](https://github.com/Orange-OpenSource/tripleflow/releases) for changelogs for each release version of Tripleflow.

The release management process is decided in the [RELEASE.md of the gh-pages branch](https://github.com/Orange-OpenSource/tripleflow/blob/gh-pages/RELEASE.md)

## Copyright and license

Code released under the MIT License.