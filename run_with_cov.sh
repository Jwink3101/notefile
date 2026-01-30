mkdir -p htmlcov/
touch htmlcov/.ignore

pytest \
    --cov=notefile \
    --cov-report html \
    --cov-report term-missing \
    tests.py