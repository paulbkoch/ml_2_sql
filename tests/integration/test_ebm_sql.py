# Make inference using both the pickled model and the SQL model
# make sure these two models have the same output
# use example data for this (titanic, although that will only cover the binary classification)
import sys

sys.path.append("scripts")

import os
import joblib
import json
import logging
import pandas as pd
import pytest
from utils.test_helpers.sql_model import execute_sql_script
from utils.output_scripts.ebm_as_code import save_model_and_extras

# Assuming your_model.pkl is the pickled model and df is the DataFrame for testing
SQL_OUTPUT_PATH = "tests/model/ebm_in_sql.sql"

# Define a list of models - datasets to test
clf_binary = [
    "tests/model/binary_ebm_classification_v051.sav",
    "input/data/example_binary_titanic.csv",
]

clf_multiclass = [
    "tests/model/multiclass_ebm_classification_v051.sav",
    "input/data/example_multiclass_faults.csv",
]

regr_regression = [
    "tests/model/regression_ebm_regression_v051.sav",
    "input/data/example_regression_used_cars.csv",
]

# combine into 1 list to iterate over
fixture_data = [clf_binary, clf_multiclass, regr_regression]


@pytest.fixture(params=fixture_data)
def load_model_data(request):
    model_path = request.param[0]
    model_type = os.path.basename(model_path).split("_")[
        0
    ]  # Binary, multiclass or regression

    with open(model_path, "rb") as f:
        model = joblib.load(f)

    data_path = request.param[1]
    data_type = os.path.basename(data_path).split("_")[
        1
    ]  # Binary, multiclass or regression

    # Load data for testing
    # Return each element of the list as a fixture value
    data = pd.read_csv(data_path)

    if model_type == data_type:
        return data, model, model_type

# paths to config files, one with and one without sql split
config_path = ["tests/configs/config_split.json", "tests/configs/config_no_split.json"]
# Define a fixture for split parameter
@pytest.fixture(params=config_path)
def post_params(request):
    config_path = request.param

    with open(config_path, "rb") as f:
        config = json.load(f)
    return config['post_params']


def test_model_processing(load_model_data, post_params, logging=logging.getLogger(__name__)):
    # unpack data and model
    data, model, model_type = load_model_data

    # Generate SQL from the loaded model
    save_model_and_extras(ebm=model, model_name="tests", post_params=post_params, logging=logging)

    # Load the SQL version
    with open(SQL_OUTPUT_PATH, "r") as sql_file:
        loaded_sql = sql_file.read()

    # logg type of model
    logging.info(f"Type: {model_type} \nSplit: {post_params['sql_split']}")   

    # Run SQL against the DataFrame using DuckDB
    if model_type == "multiclass":
        prob_column = "probability_Z_Scratch"
    elif model_type == "binary":
        prob_column = "probability"
    elif model_type == "regression":
        prob_column = "prediction"

    sql_pred = execute_sql_script(loaded_sql, data, prob_column)

    # Add assertions to check if the results are as expected
    assert sql_pred is not None

    # Predict scores using pickled model
    if model_type == "multiclass":
        model_pred = model.predict_proba(data)[:,-1]
    elif model_type == "binary":
        model_pred = model.predict_proba(data)[:,1]
    elif model_type == "regression":
        model_pred = model.predict(data)

    logging.info(
        f"Max difference SQL - pickled model: {(abs((sql_pred - model_pred)/model_pred)).max()}"
    )

    # Check if SQL model prediction is same as pickled model prediction
    # use a tolerance of 0.001%
    tolerance = 0.00001
    assert (abs((sql_pred - model_pred) / model_pred) <= tolerance).all()

    # Clean up: Delete the generated SQL file after the test
    import os

    os.remove(SQL_OUTPUT_PATH)
