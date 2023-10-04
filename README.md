# WP4 Analytics API

[![Actions Status][actions badge]][actions]
[![CodeCov][codecov badge]][codecov]
[![LICENSE][license badge]][license]

<!-- Links -->
[actions]: https://github.com/sifis-home/analytics_api/actions
[codecov]: https://codecov.io/gh/sifis-home/analytics_api
[license]: LICENSES/MIT.txt

<!-- Badges -->
[actions badge]: https://github.com/sifis-home/analytics_api/workflows/analytics_api/badge.svg
[codecov badge]: https://codecov.io/gh/sifis-home/analytics_api/branch/master/graph/badge.svg
[license badge]: https://img.shields.io/badge/license-MIT-blue.svg


## Deploying

### Analytics API in a container

Analytics API is intended to run in a docker container. The Dockerfile at the root of this repo describes the container. To build and run it execute the following commands:

`docker build -t analytics_api .`

`docker-compose up`

## License

Released under the [MIT License](LICENSE).

## Acknowledgements

This software has been developed in the scope of the H2020 project SIFIS-Home with GA n. 952652.
