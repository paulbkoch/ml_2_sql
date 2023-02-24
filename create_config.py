import csv
import json
import os

def get_input(options, message):
    print(f"\n{message}")
    choice = None
    while choice is None:
        for i, option in enumerate(options):
            print(f"{i + 1}. {option}")
        response = input("Enter the number of your choice: ")
        try:
            choice = options[int(response) - 1]
        except (ValueError, IndexError):
            print("Invalid option, try again.")
    return choice

# List files in input/data/ directory
data_dir = "input/data/"
files = os.listdir(data_dir)

print("Files in input/data/:")
for i, file in enumerate(files, 1):
    print(f"{i}. {file}")

# Ask for CSVPATH
csv_path = None
while csv_path is None:
    csv_file_index = input("\nSelect path to csv file to create config for: ")
    try:
        csv_file_index = int(csv_file_index) - 1
        csv_path = os.path.join(data_dir, files[csv_file_index])
    except (ValueError, IndexError):
        print("Invalid option, try again.")

print(f"CSV file {csv_path} will be used to create a config file for")

# Load the example CSV file
with open(csv_path) as f:
    reader = csv.reader(f)
    headers = next(reader)

# Create a dictionary to store the features and their indices
features_dict = {}
for i, header in enumerate(headers):
    features_dict[i] = header

# Ask the user to choose a target
print("Which column would you like to use as the target?")
for i, header in features_dict.items():
    print(f"{i}. {header}")
target = int(input("Enter the index of the target column: "))

# Remove the target from the list of features
target_column = features_dict.pop(target)

# Initialize the selected features
selected_features = []

# Main loop to prompt the user for feature selection
while True:
    print("\nFeatures:")
    for i, header in features_dict.items():
        if i in selected_features:
            print(f"{i}: {header} (selected)")
        else:
            print(f"{i}: {header}")
    print("\nSelect features:")
    print("1. Choose a feature by index")
    print("2. Deselect a feature by index")
    print("3. Select all features")
    print("4. Deselect all features")
    print("5. Done")
    choice = input("Enter your choice (1-5): ")

    # Check the user's choice
    if choice == "1":
        index = int(input("Enter the index of the feature you want to select: "))
        if index in features_dict.keys() and index not in selected_features:
            selected_features.append(index)
    elif choice == "2":
        index = int(input("Enter the index of the feature you want to deselect: "))
        if index in selected_features:
            selected_features.remove(index)
    elif choice == "3":
        selected_features = list(features_dict.keys())
    elif choice == "4":
        selected_features = []
    elif choice == "5":
        break
    else:
        print("Invalid choice. Please try again.")

# Create the features list from the selected features indices
features = [features_dict[i] for i in selected_features]

# Non used columns
[features_dict.pop(i) for i in selected_features]

# Fill in the JSON template with the selected features
input_params = {
  "features": features,
  "model_params": {
  },
  "post_params": {
    "calibration": "false",
    "sql_split": "true",
    "file_type": "html"
  },
  "pre_params": {
    "cv_type": "notimeseriesplit",
    "max_rows": 100000,
    "time_sensitive_column": "date_column",
    "upsampling": "false"
  },
  "target": target_column
}

# Ask the user to input the value for each key in input_params
print("\nLet's fill in the rest of the JSON file together!\n")

for key in input_params:
    if key in ["features", "target"]:
        continue
    elif key == "model_params":
        input_value = input("Do you have any specific model parameters to set? (yes/no): ")
        if input_value.lower() == "yes":
            model_params = {}
            model_params_keys = input("Enter the key for each model parameter, separated by comma: ").split(',')
            model_params_values = input("Enter the value for each model parameter, separated by comma: ").split(',')
            for i in range(len(model_params_keys)):
                model_params[model_params_keys[i].strip()] = model_params_values[i].strip()
            input_params[key] = model_params
        else:
            print("No model parameters were set.\n")
    else:
        if len(input_params[key]) > 1:
            for key2 in input_params[key]:
                if key2 == 'calibration':
                    # input_value = get_input(["true","false"], "Calibration (true/false): ")
                    input_value = "false"
                elif key2 == 'sql_split':
                    input_value = get_input(["true","false"], "SQL split (true/false): ")
                elif key2 == 'file_type':
                    input_value = get_input(["html","png"], "File type (html/png): ")
                elif key2 == 'cv_type':
                    input_value = get_input(["timeseriessplit","kfold"], "CV type (timeseriessplit/kfold): ")
                elif key2 == 'max_rows':
                    input_value = int(input("\nMax rows (number): "))
                elif key2 == 'time_sensitive_column':
                    if input_params['pre_params']['cv_type'] == 'timeseriessplit':
                        if len(features_dict) == 0:
                            print('No columns to select as time sensitive, switching to kfold')
                            input_params['pre_params']['cv_type'] = 'kfold'
                        print("\nWhich column would you like to use as the time sensitive column?")
                        for i, header in features_dict.items():
                            print(f"{i}. {header}")
                        date_col_index = int(input("Enter the index of the time sensitive column: "))
                        input_value = features_dict[date_col_index]
                    else:
                        input_value = '_'
                elif key2 == 'upsampling':
                    # input_value = get_input(["true","false"], "Upsampling (true/false): ")
                    input_value = "false"
                
                # Fill in value in dict
                input_params[key][key2] = input_value

# convert the dictionary to a JSON string
json_string = json.dumps(input_params, indent=4)

# name config file
config_name = input("\nName config file:")
config_name = config_name.split(".")[0]

# write the JSON string to a file
with open(f"input/configuration/{config_name}.json", "w") as file:
    file.write(json_string)

# Print the resulting JSON
print(json_string)