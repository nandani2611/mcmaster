import json
import csv
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime

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

def format_additional_attributes(attributes, mapped_fields):
    """Format the additional attributes, excluding fields that were explicitly mapped."""
    formatted = []
    for k, v in attributes.items():
        # Skip fields that were mapped to specific columns
        if k in mapped_fields:
            continue
        if v is None:
            continue
        if isinstance(v, bool):
            v = 'Yes' if v else 'No'
        elif isinstance(v, (dict, list)):
            v = json.dumps(v)
        formatted.append(f"{k}={v}")
    return ", ".join(formatted)

def json_to_csv(input_file, output_file=None, delimiter=','):
    """Convert JSON to CSV with specific Magento format and field mappings."""
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
    
    # Define the fixed Magento columns
    magento_columns = [
        'sku', 'store_view_code', 'attribute_set_code', 'product_type', 'categories',
        'product_websites', 'name', 'description', 'short_description', 'weight',
        'product_online', 'tax_class_name', 'visibility', 'price', 'special_price',
        'special_price_from_date', 'special_price_to_date', 'url_key', 'meta_title',
        'meta_keywords', 'meta_description', 'created_at', 'updated_at', 'new_from_date',
        'new_to_date', 'display_product_options_in', 'map_price', 'msrp_price',
        'map_enabled', 'gift_message_available', 'custom_design', 'custom_design_from',
        'custom_design_to', 'custom_layout_update', 'page_layout', 'product_options_container',
        'msrp_display_actual_price_type', 'country_of_manufacture', 'additional_attributes',
        'qty', 'out_of_stock_qty', 'use_config_min_qty', 'is_qty_decimal', 'allow_backorders',
        'use_config_backorders', 'min_cart_qty', 'use_config_min_sale_qty', 'max_cart_qty',
        'use_config_max_sale_qty', 'is_in_stock', 'notify_on_stock_below', 'use_config_notify_stock_qty',
        'manage_stock', 'use_config_manage_stock', 'use_config_qty_increments', 'qty_increments',
        'use_config_enable_qty_inc', 'enable_qty_increments', 'is_decimal_divided', 'website_id',
        'deferred_stock_update', 'use_config_deferred_stock_update', 'related_skus', 'crosssell_skus',
        'upsell_skus', 'hide_from_product_page', 'custom_options', 'bundle_price_type',
        'bundle_sku_type', 'bundle_price_view', 'bundle_weight_type', 'bundle_values', 'associated_skus'
    ]
    
    # Define field mappings from JSON to Magento columns
    field_mappings = {
        '_id_$oid': 'sku',
        'title': 'name',
        'description': 'description',
        'category': 'categories',
        'subcategory': 'categories',
        'data_Each': 'qty',
        'data_Pkg._Qty.': 'qty',
        'data_Tensile_Strength,_psi': 'additional_attributes',
        'data_Property A': 'additional_attributes',
        'data_Property B': 'additional_attributes',
        'data_Specifications_Met': 'additional_attributes',
        'images': 'additional_attributes',
        'link': 'url_key',
        'timestamp': 'created_at',
        'data_Dia.,_mm': 'weight',
        'data_Ht.,_mm': 'weight',
        'data_Lg.,_mm': 'weight'
    }
        
    # Process all records
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
                combined_attributes = flattened_main.copy()
                for k, v in data_item.items():
                    combined_attributes[f"data_{k}"] = v
                
                # Create Magento record with default values
                magento_record = {col: '' for col in magento_columns}
                
                # Set default values
                magento_record['attribute_set_code'] = ''
                magento_record['product_type'] = ''
                magento_record['product_online'] = ''
                magento_record['tax_class_name'] = ''
                magento_record['visibility'] = ''
                magento_record['is_in_stock'] = ''
                magento_record['manage_stock'] = ''
                magento_record['categories'] = ''
                magento_record['product_websites'] = ''
                
                # Apply field mappings
                mapped_fields = set()
                for json_field, magento_field in field_mappings.items():
                    if json_field in combined_attributes:
                        magento_record[magento_field] = combined_attributes[json_field]
                        mapped_fields.add(json_field)
                
                # Set the additional attributes (excluding mapped fields)
                magento_record['additional_attributes'] = format_additional_attributes(
                    combined_attributes, mapped_fields
                )
                
                processed_records.append(magento_record)
        else:
            # Create Magento record without data fields
            magento_record = {col: '' for col in magento_columns}
            
            # Set default values
            magento_record['attribute_set_code'] = ''
            magento_record['product_type'] = ''
            magento_record['product_online'] = ''
            magento_record['tax_class_name'] = ''
            magento_record['visibility'] = ''
            magento_record['is_in_stock'] = ''
            magento_record['manage_stock'] = ''
            magento_record['categories'] = ''
            magento_record['product_websites'] = ''
            
            # Apply field mappings
            mapped_fields = set()
            for json_field, magento_field in field_mappings.items():
                if json_field in flattened_main:
                    magento_record[magento_field] = flattened_main[json_field]
                    mapped_fields.add(json_field)
            
            # Set the additional attributes (excluding mapped fields)
            magento_record['additional_attributes'] = format_additional_attributes(
                flattened_main, mapped_fields
            )
            
            processed_records.append(magento_record)
    
    # Write CSV file
    with open(output_file, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=magento_columns, delimiter=delimiter)
        writer.writeheader()
        
        for record in processed_records:
            writer.writerow(record)
    
    print(f"Successfully converted {input_file} to {output_file}")
    print(f"Total columns: {len(magento_columns)}")
    print(f"Processed records: {len(processed_records)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert JSON to CSV with Magento format')
    parser.add_argument('input_file', help='Path to the input JSON file')
    parser.add_argument('-o', '--output', help='Path to the output CSV file')
    parser.add_argument('-d', '--delimiter', default=',', 
                       help='CSV delimiter (default: comma)')
    
    args = parser.parse_args()
    
    json_to_csv(
        input_file=args.input_file,
        output_file=args.output,
        delimiter=args.delimiter
    )