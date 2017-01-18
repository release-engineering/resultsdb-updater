from setuptools import setup, find_packages

with open('requirements.txt', 'r') as f:
    requirements = f.readlines()

with open('test-requirements.txt', 'r') as f:
    test_requirements = f.readlines()


setup(
    name='resultsdb-updater',
    version='2.0.0',
    description='A micro-service that listens for messages on the message bus and updates ResultsDB',
    license='GPLv2+',
    author='Matt Prahl',
    author_email='mprahl@redhat.com',
    url='https://github.com/release-engineering/resultsdb-updater',
    install_requires=requirements,
    tests_require=test_requirements,
    packages=find_packages(),
    include_data=True,
    entry_points="""
    [moksha.consumer]
    ciconsumer = resultsdbupdater.consumer:CIConsumer
    """,
)
