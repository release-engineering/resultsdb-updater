# ResultsDB-Updater

ResultsDB-Updater is a micro-service that listens for test results on the CI
message bus and updates ResultsDB in a standard format.

### Installation

Install the Python dependencies:

```
pip install -r requirements.txt
```

Edit the configuration file at:

```
fedmsg.d/config.py
```

Generate the entry points for fedmsg-hub:

```
python setup.py egg_info
```

Run the service:

```
fedmsg-hub
```
