"""Single source of truth for every threshold the analysis depends on.

Why a config file?
    In v1 the numbers 8, 6, 30, 0.20 ... were scattered through the notebook.
    If an interviewer asks "what if the cutoff were 20 minutes?", you should be
    able to change ONE line here and re-run everything.
"""

# --- Data ---------------------------------------------------------------
# TLC license codes for High-Volume For-Hire Vehicle (HVFHV) companies.
LICENSE_MAP = {"HV0002": "Juno", "HV0003": "Uber", "HV0004": "Via", "HV0005": "Lyft"}

# Only these columns are read from the parquet file (columnar storage lets us
# skip the rest, which saves a lot of memory on a ~19M-row month).
TRIP_COLUMNS = [
    "hvfhs_license_num",
    "request_datetime",
    "on_scene_datetime",
    "pickup_datetime",
    "dropoff_datetime",
    "PULocationID",
    "DOLocationID",
    "trip_miles",
    "trip_time",
    "base_passenger_fare",
    "tips",
    "driver_pay",
    "shared_request_flag",
    "shared_match_flag",
    "wav_request_flag",
    "wav_match_flag",
]

# --- Cleaning -----------------------------------------------------------
# A request-to-arrival time outside [0, 30] minutes is treated as a data
# error / extreme outlier. Use quality.cutoff_sensitivity() to show the
# results do not hinge on this choice.
ETA_MIN_VALID = 0.0
ETA_MAX_VALID = 30.0

# --- Time features ------------------------------------------------------
# Commute windows. Applied on WEEKDAYS only (see prepare_trips).
RUSH_HOURS = (7, 8, 9, 16, 17, 18, 19)
WINDOW_MINUTES = 10  # the PRD's "10-minute window"

# --- Product thresholds (from the PRD) ----------------------------------
LONG_WAIT_MIN = 8.0     # a wait above this is a "bad experience" (PRD: >8 min)
ETA_TARGET_MIN = 6.0    # guardrail: average pickup wait should stay under this

# --- Statistical reliability guards -------------------------------------
MIN_TRIPS_ZONE = 500    # ignore zones with fewer trips (too noisy to rank)
MIN_TRIPS_WINDOW = 5    # a zone-10-minute window needs >= this many trips

# --- Incentive policy (from the PRD) ------------------------------------
TRIGGER_THRESHOLD = 0.20   # trigger when stress rate > 20 %
BASE_BONUS = 2.00          # dollars
RATE_MULTIPLIER = 5.00     # dollars per 1.0 (=100 %) of stress rate
ACTIVE_WINDOWS = 3         # a bonus stays live for 3 x 10 min = 30 min
BUDGET_CAP_PER_RIDE = 2.50 # guardrail, interpreted as blended $/ride (see docs)

# --- Experiment design --------------------------------------------------
ALPHA = 0.05
POWER = 0.80

RANDOM_SEED = 42
