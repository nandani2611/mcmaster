import json
import csv
import argparse
from pathlib import Path
from collections import defaultdict

def flatten_dict(d, parent_key='', sep='_'):
    """Flatten a nested dictionary structure."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Handle arrays - convert to JSON string if not empty
            items.append((new_key, json.dumps(v) if v else None))
        else:
            items.append((new_key, v))
    return dict(items)

def process_data_array(data_array):
    """Process the nested data array structure."""
    all_fields = set()
    processed_data = []
    
    for sub_array in data_array:
        if not sub_array:  # Skip empty arrays
            continue
        for item in sub_array:
            flattened = flatten_dict(item)
            processed_data.append(flattened)
            all_fields.update(flattened.keys())
    
    return processed_data, sorted(all_fields)

def json_to_csv(input_file, output_file=None, delimiter=',', null_value='NULL'):
    """Convert JSON to CSV with all keys as columns."""
    if output_file is None:
        input_path = Path(input_file)
        output_file = input_path.with_suffix('.csv')
    
    with open(input_file, 'r', encoding='utf-8') as json_file:
        try:
            data = json.load(json_file)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON file: {e}")
            return
    
    if not isinstance(data, list):
        data = [data]
    
    if not data:
        print("No data found in JSON file")
        return
    
    # Process all records
    all_fields = set()
    processed_records = []
    
    for record in data:
        # Flatten main record (excluding data field)
        main_record = {k: v for k, v in record.items() if k != 'data'}
        flattened_main = flatten_dict(main_record)
        
        # Process data array separately
        if 'data' in record:
            processed_data, data_fields = process_data_array(record['data'])
            # Add data fields to the main record with data_ prefix
            for data_item in processed_data:
                combined_record = flattened_main.copy()
                for k, v in data_item.items():
                    combined_record[f"data_{k}"] = v
                processed_records.append(combined_record)
                all_fields.update(combined_record.keys())
        else:
            processed_records.append(flattened_main)
            all_fields.update(flattened_main.keys())
    
    # Sort fields alphabetically
    fieldnames = sorted(all_fields)
    
    # Write CSV file
    with open(output_file, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        
        for record in processed_records:
            # Fill missing fields with NULL
            complete_record = {field: record.get(field, null_value) for field in fieldnames}
            writer.writerow(complete_record)
    
    print(f"Successfully converted {input_file} to {output_file}")
    print(f"Total columns: {len(fieldnames)}")
    print(f"Processed records: {len(processed_records)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert JSON to CSV with all keys as columns')
    parser.add_argument('input_file', help='Path to the input JSON file')
    parser.add_argument('-o', '--output', help='Path to the output CSV file')
    parser.add_argument('-d', '--delimiter', default=',', 
                       help='CSV delimiter (default: comma)')
    parser.add_argument('-n', '--null', default='NULL',
                       help='Value to use for NULL/missing data (default: NULL)')
    
    args = parser.parse_args()
    
    json_to_csv(
        input_file=args.input_file,
        output_file=args.output,
        delimiter=args.delimiter,
        null_value=args.null
    )