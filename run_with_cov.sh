mkdir -p htmlcov/
touch htmlcov/.ignore

pytest --cov=notefile --cov-report html tests.py