import requests
import fitz  # PyMuPDF
import pandas as pd
import numpy as np
import ast , re
import json
from playwright.sync_api import sync_playwright
import os
from .chat_with_ollama import chat

def frequency_overlap_ratio(min1, max1, min2, max2):
    """
    Return the overlap ratio between two frequency intervals.
    - 1.0  : intervals overlap completely (identical or one contains the other)
    - 0.0  : intervals do not overlap at all
    Handles zero‑length intervals (fixed frequencies) without
    dividing by zero.
    """
    # ----- Handle fixed points ---------------------------------
    # both are single points
    if min1 == max1 and min2 == max2:
        return 1.0 if min1 == min2 else 0.0
    # first interval is a single point
    if min1 == max1:
        return 1.0 if min1 <= max2 else 0.0
    # second interval is a single point
    if min2 == max2:
        return 1.0 if max1 <= min2 else 0.0
    # ----- Regular interval overlap ----------------------------
    overlap_min = max(min1, min2)
    overlap_max = min(max1, max2)
    overlap_length = max(0, overlap_max - overlap_min)
    # lengths of the two intervals
    ratio = max1 - min1          # <-- this is NOT the *overlap* ratio!
    len2 = max2 - min2
    # shortest = min(len1, len2)
    # shortest cannot be 0 here because we already handled points
    return overlap_length/ratio

def algorithm_buck_boost():
    print("")
# from boost import boost
def algorithm_buck(response:str ,
              boolean_package : str,
              tol :float = 100,
              top_n :int = 10,
              min_freq_overlap_ratio :float = 0.1
              ):
    
    import re, json

    # 1) Grab the first [...] block
    m = re.search(r'\[.*\]', response, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON array foundn response!")
    array_text = m.group(0)
    # print("array_text:", array_text)
    # 2) Now parse it
    values = json.loads(array_text)

    # 3) Zip into your dict
    keys = ["Topology","Vin_min","Vin_max","Iout", "Freq_min", "Freq_max","Package", "Width" , "Length"]
    part_specs = dict(zip(keys, values))

    # part_specs['Package Size'] = format_dimensions(part_specs['Package Size'])    #competitor part specs 
    
    print(part_specs) 
    # print("done")
    # 2. Load dataset
    df = pd.read_excel('MPS_database.xlsx')
  
    # print(df.dtypes)
    print("done")

    comp_spec = part_specs


    print("range in here")
    mask = (
        (np.abs(df['Vin_min'] - comp_spec['Vin_min']) <= tol * comp_spec['Vin_min']) &
        (np.abs(df['Vin_max'] - comp_spec['Vin_max']) <= tol * comp_spec['Vin_max']) &
        (np.abs(df['Iout']    - comp_spec['Iout'])    <= tol * comp_spec['Iout']) 
    )

    # 1.2-1 = 0.2 <= 0.5x1 = 0.5

    # -----------------------
    # 5) Frequency range overlap filter
    # -----------------------

    if (comp_spec['Freq_min'] == comp_spec['Freq_max']) :
        print("test_case1")
        freq_mask2 = (df['Freq_min'] == df['Freq_max']) & (df['Freq_min'] == comp_spec['Freq_min'])
        
        # Also, filter rows where single frequency is within the range of varying frequencies
        freq_mask_var = (df['Freq_min'] != df['Freq_max']) & ((df['Freq_min'] <= comp_spec['Freq_min']) & (df['Freq_max'] >= comp_spec['Freq_min']))    
        # print(freq_mask_var)
        mask &= freq_mask2 | freq_mask_var  # Combine the two masks

        
    else:
        print("test case 2")
        freq_mask_range = (df['Freq_min'] != df['Freq_max']) & df.apply(
            lambda row: frequency_overlap_ratio(
                comp_spec['Freq_min'], comp_spec['Freq_max'],
                row['Freq_min'], row['Freq_max']
            ) >= min_freq_overlap_ratio,
            axis=1
        )

        freq_mask_var2 = (df['Freq_min'] == df['Freq_max']) & (df['Freq_min'] <= comp_spec['Freq_max']) & (df['Freq_max'] >= comp_spec['Freq_min'])
        mask &= freq_mask_var2 | freq_mask_range
         
    
    if boolean_package == 'yes':
        mask &= (df['Package']      == comp_spec['Package'])
        mask &= (abs(df['Width'] - comp_spec['Width']) == 0)
        mask &= (abs(df['Length'] - comp_spec['Length']) == 0)
    mask &= (df['Topology']     == comp_spec['Topology'])

    # print(mask)
    cand = df[mask].copy()
    print(cand)

    for field in ['Vin_min', 'Vin_max', 'Iout']:
        comp = comp_spec[field]
        cand[f'{field}_sim'] = (
            1 - (cand[field] - comp).abs() / comp
        ).clip(0, 1)                     # 0 … 1  (exact match → 1)
 
    # Frequency similarity = actual overlap ratio
    cand['Freq_sim'] = cand.apply(
        lambda row: frequency_overlap_ratio(
            comp_spec['Freq_min'], comp_spec['Freq_max'],
            row['Freq_min'], row['Freq_max']
        ),
        axis=1
    )
    
    # 4) Weighted sum — now only numeric fields:

    weights = {

        'Vin_min_sim': 0.25,

        'Vin_max_sim': 0.25,

        'Iout_sim':    0.25,

        'Freq_sim':    0.25,

    }

    # normalize

    total_w = sum(weights.values())

    weights = {k: v/total_w for k,v in weights.items()}

    cand['Score'] = sum(cand[k]*w for k,w in weights.items()) 


    return (

        cand.sort_values('Score', ascending=False)

            [['PartNumber','Score',"Topology","Vin_min","Vin_max","Iout", "Freq_min", "Freq_max","Package", "Width" , "Length"]]

            .head(top_n)

    )

def algorithm_boost(response:str ,
              boolean_package : str,
              tol :float = 20,
              top_n :int = 10,
              min_freq_overlap_ratio :float = 0.1
              ):
    
    print(top_n)
    import re, json

    # 1) Grab the first [...] block
    m = re.search(r'\[.*\]', response, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON array foundn response!")
    array_text = m.group(0)
    # print("array_text:", array_text)
    # 2) Now parse it
    values = json.loads(array_text)
    
    # 3) Zip into your dict
    keys = ["Topology", "Vin_min","Vin_max", "Freq_min", "Freq_max","Package", "Width" , "Length","Vout_min" , "Vout_max" , "IQ"]
    part_specs = dict(zip(keys, values))

    # part_specs['Package Size'] = format_dimensions(part_specs['Package Size'])    #competitor part specs 
    
    print(part_specs) 
    # print("done")
    # 2. Load dataset
    df = pd.read_excel('MPS_database.xlsx')
  
    # print(df.dtypes)
    print("done")

    comp_spec = part_specs


    print("range in here")
    mask = (
        (np.abs(df['Vin_min'] - comp_spec['Vin_min']) <= tol * comp_spec['Vin_min']) &
        (np.abs(df['Vin_max'] - comp_spec['Vin_max']) <= tol * comp_spec['Vin_max']) &
        (np.abs(df['Vout_min'] - comp_spec['Vout_min']) <= tol * comp_spec['Vout_min']) &
        (np.abs(df['Vout_max'] - comp_spec['Vout_max']) <= tol * comp_spec['Vout_max']) &
        (np.abs(df['IQ']    - comp_spec['IQ'])  <= tol * comp_spec['IQ']) 
    )

    # 1.2-1 = 0.2 <= 0.5x1 = 0.5

    # -----------------------
    # 5) Frequency range overlap filter
    # -----------------------

    if (comp_spec['Freq_min'] == comp_spec['Freq_max']) :
        print("test_case1")
        freq_mask2 = (df['Freq_min'] == df['Freq_max']) & (df['Freq_min'] == comp_spec['Freq_min'])
        
        # Also, filter rows where single frequency is within the range of varying frequencies
        freq_mask_var = (df['Freq_min'] != df['Freq_max']) & ((df['Freq_min'] <= comp_spec['Freq_min']) & (df['Freq_max'] >= comp_spec['Freq_min']))    
        # print(freq_mask_var)
        mask &= freq_mask2 | freq_mask_var  # Combine the two masks

        
    else:
        print("test case 2")
        freq_mask_range = (df['Freq_min'] != df['Freq_max']) & df.apply(
            lambda row: frequency_overlap_ratio(
                comp_spec['Freq_min'], comp_spec['Freq_max'],
                row['Freq_min'], row['Freq_max']
            ) >= min_freq_overlap_ratio,
            axis=1
        )

        freq_mask_var2 = (df['Freq_min'] == df['Freq_max']) & (df['Freq_min'] <= comp_spec['Freq_max']) & (df['Freq_max'] >= comp_spec['Freq_min'])
        mask &= freq_mask_var2 | freq_mask_range
         
    
    if boolean_package == 'yes':
        mask &= (df['Package']      == comp_spec['Package'])
        mask &= (abs(df['Width'] - comp_spec['Width']) == 0)
        mask &= (abs(df['Length'] - comp_spec['Length']) == 0)
    mask &= (df['Topology']     == comp_spec['Topology'])

    # print(mask)
    cand = df[mask].copy()
    print(cand)

    for field in ['Vin_min', 'Vin_max', 'Vout_min', 'Vout_max','IQ']:
        comp = comp_spec[field]
        cand[f'{field}_sim'] = (
            1 - (cand[field] - comp).abs() / comp
        ).clip(0, 1)                     # 0 … 1  (exact match → 1)
 
    # Frequency similarity = actual overlap ratio
    cand['Freq_sim'] = cand.apply(
        lambda row: frequency_overlap_ratio(
            comp_spec['Freq_min'], comp_spec['Freq_max'],
            row['Freq_min'], row['Freq_max']
        ),
        axis=1
    )
    

    # 4) Weighted sum — now only numeric fields:

    weights = {

        'Vin_min_sim': 0.25,

        'Vin_max_sim': 0.25,

        'IQ_sim':    0.25,

        'Freq_sim':    0.25,

        'Vout_min_sim' : 0.25,

        'Vout_max_sim' : 0.25

    }

    # normalize

    total_w = sum(weights.values())

    weights = {k: v/total_w for k,v in weights.items()}

    cand['Score'] = sum(cand[k]*w for k,w in weights.items()) 

    print(top_n)

    return (

        cand.sort_values('Score', ascending=False)

            [['PartNumber','Score',"Topology","Vin_min","Vin_max","Iout", "Freq_min", "Freq_max","Package", "Width" , "Length"]]

            .head(top_n)

    )

