def pytest_addoption(parser):
    parser.addoption('--test_parameters', action='store', help='Parameters for tests')