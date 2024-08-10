import pandas as pd

# Load the JSON data
data = pd.read_json('data.json')

# Convert the data to a CSV file
data.to_csv('data1.csv', index=False)

data.head()


#something 